#!/usr/bin/env python3
"""
Backend API Testing for Colorify Manga
Tests all backend endpoints with comprehensive validation
"""

import requests
import base64
import io
import json
from PIL import Image, ImageDraw
import time
import os
from pathlib import Path

# Configuration
BACKEND_URL = "https://mangapalette.preview.emergentagent.com/api"
TEST_USER_ID = "test_user_123"
TEST_MODEL_ID = "TencentARC/ColorFlow"

class ColorifyMangaAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_user_id = TEST_USER_ID
        self.test_model_id = TEST_MODEL_ID
        self.session = requests.Session()
        self.test_results = []
        self.created_colorization_id = None
        
    def log_result(self, test_name, success, message, response_data=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if response_data and not success:
            print(f"   Response: {response_data}")
    
    def create_test_image(self):
        """Create a simple black and white test image"""
        # Create a simple black and white manga-style image
        img = Image.new('RGB', (400, 300), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw some simple manga-style elements
        # Character outline
        draw.ellipse([150, 50, 250, 150], outline='black', width=3)  # Head
        draw.rectangle([175, 150, 225, 250], outline='black', width=2)  # Body
        
        # Simple features
        draw.ellipse([170, 80, 180, 90], fill='black')  # Left eye
        draw.ellipse([220, 80, 230, 90], fill='black')  # Right eye
        draw.arc([185, 100, 215, 120], 0, 180, fill='black', width=2)  # Smile
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()
    
    def test_health_check(self):
        """Test GET /api/health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_result("Health Check", True, "Health endpoint responding correctly", data)
                    return True
                else:
                    self.log_result("Health Check", False, f"Unexpected health status: {data.get('status')}", data)
                    return False
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_root_endpoint(self):
        """Test GET /api/ endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "endpoints" in data:
                    self.log_result("Root Endpoint", True, "Root endpoint returning API info", data)
                    return True
                else:
                    self.log_result("Root Endpoint", False, "Missing expected fields in response", data)
                    return False
            else:
                self.log_result("Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_colorize_manga(self):
        """Test POST /api/colorize endpoint"""
        try:
            # Create test image
            test_image_bytes = self.create_test_image()
            
            # Prepare multipart form data
            files = {
                'file': ('test_manga.png', test_image_bytes, 'image/png')
            }
            data = {
                'user_id': self.test_user_id,
                'model_id': self.test_model_id
            }
            
            print(f"Uploading test image ({len(test_image_bytes)} bytes) for colorization...")
            response = self.session.post(
                f"{self.base_url}/colorize", 
                files=files, 
                data=data, 
                timeout=180  # Extended timeout for AI processing
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'user_id', 'original_image', 'colorized_image', 'model_id', 'created_at']
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_result("Colorize Manga", False, f"Missing fields: {missing_fields}", data)
                    return False
                
                # Validate base64 images
                if not data['original_image'].startswith('data:image'):
                    self.log_result("Colorize Manga", False, "Original image not in proper base64 format")
                    return False
                
                if not data['colorized_image'].startswith('data:image'):
                    self.log_result("Colorize Manga", False, "Colorized image not in proper base64 format")
                    return False
                
                # Store colorization ID for later tests
                self.created_colorization_id = data['id']
                
                self.log_result("Colorize Manga", True, f"Successfully colorized image. ID: {data['id']}")
                return True
                
            elif response.status_code == 429:
                self.log_result("Colorize Manga", False, "Rate limit exceeded - HuggingFace API limit reached", response.text)
                return False
            elif response.status_code == 400:
                self.log_result("Colorize Manga", False, f"Bad request: {response.text}")
                return False
            else:
                self.log_result("Colorize Manga", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Colorize Manga", False, f"Error during colorization: {str(e)}")
            return False
    
    def test_colorize_invalid_file(self):
        """Test POST /api/colorize with invalid file format"""
        try:
            # Create a text file instead of image
            files = {
                'file': ('test.txt', b'This is not an image', 'text/plain')
            }
            data = {
                'user_id': self.test_user_id,
                'model_id': self.test_model_id
            }
            
            response = self.session.post(f"{self.base_url}/colorize", files=files, data=data, timeout=30)
            
            if response.status_code == 400:
                self.log_result("Colorize Invalid File", True, "Correctly rejected invalid file format")
                return True
            else:
                self.log_result("Colorize Invalid File", False, f"Should have returned 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Colorize Invalid File", False, f"Error testing invalid file: {str(e)}")
            return False
    
    def test_get_user_colorizations(self):
        """Test GET /api/colorizations/{user_id} endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/colorizations/{self.test_user_id}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    if len(data) > 0:
                        # Validate structure of first colorization
                        first_item = data[0]
                        required_fields = ['id', 'user_id', 'original_image', 'colorized_image', 'model_id', 'created_at']
                        missing_fields = [field for field in required_fields if field not in first_item]
                        
                        if missing_fields:
                            self.log_result("Get User Colorizations", False, f"Missing fields in colorization: {missing_fields}")
                            return False
                        
                        self.log_result("Get User Colorizations", True, f"Retrieved {len(data)} colorizations for user")
                        return True
                    else:
                        self.log_result("Get User Colorizations", True, "No colorizations found for user (empty array)")
                        return True
                else:
                    self.log_result("Get User Colorizations", False, "Response is not an array", data)
                    return False
            else:
                self.log_result("Get User Colorizations", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get User Colorizations", False, f"Error fetching colorizations: {str(e)}")
            return False
    
    def test_get_nonexistent_user_colorizations(self):
        """Test GET /api/colorizations/{user_id} with non-existent user"""
        try:
            fake_user_id = "nonexistent_user_999"
            response = self.session.get(f"{self.base_url}/colorizations/{fake_user_id}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) == 0:
                    self.log_result("Get Nonexistent User Colorizations", True, "Correctly returned empty array for nonexistent user")
                    return True
                else:
                    self.log_result("Get Nonexistent User Colorizations", False, f"Unexpected response for nonexistent user: {data}")
                    return False
            else:
                self.log_result("Get Nonexistent User Colorizations", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Get Nonexistent User Colorizations", False, f"Error testing nonexistent user: {str(e)}")
            return False
    
    def test_delete_colorization(self):
        """Test DELETE /api/colorizations/{colorization_id} endpoint"""
        if not self.created_colorization_id:
            self.log_result("Delete Colorization", False, "No colorization ID available for deletion test")
            return False
        
        try:
            response = self.session.delete(f"{self.base_url}/colorizations/{self.created_colorization_id}", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "deleted" in data["message"].lower():
                    self.log_result("Delete Colorization", True, f"Successfully deleted colorization {self.created_colorization_id}")
                    return True
                else:
                    self.log_result("Delete Colorization", False, f"Unexpected delete response: {data}")
                    return False
            else:
                self.log_result("Delete Colorization", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Delete Colorization", False, f"Error deleting colorization: {str(e)}")
            return False
    
    def test_delete_nonexistent_colorization(self):
        """Test DELETE /api/colorizations/{colorization_id} with invalid ID"""
        try:
            fake_id = "nonexistent_colorization_999"
            response = self.session.delete(f"{self.base_url}/colorizations/{fake_id}", timeout=30)
            
            if response.status_code == 404:
                self.log_result("Delete Nonexistent Colorization", True, "Correctly returned 404 for nonexistent colorization")
                return True
            else:
                self.log_result("Delete Nonexistent Colorization", False, f"Should have returned 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Delete Nonexistent Colorization", False, f"Error testing nonexistent colorization: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend API tests"""
        print(f"🚀 Starting Colorify Manga Backend API Tests")
        print(f"📡 Backend URL: {self.base_url}")
        print(f"👤 Test User ID: {self.test_user_id}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Root Endpoint", self.test_root_endpoint),
            ("Colorize Manga", self.test_colorize_manga),
            ("Colorize Invalid File", self.test_colorize_invalid_file),
            ("Get User Colorizations", self.test_get_user_colorizations),
            ("Get Nonexistent User", self.test_get_nonexistent_user_colorizations),
            ("Delete Colorization", self.test_delete_colorization),
            ("Delete Nonexistent", self.test_delete_nonexistent_colorization),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_result(test_name, False, f"Test execution error: {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check details above.")
        
        return passed, total, self.test_results

def main():
    """Main test execution"""
    tester = ColorifyMangaAPITester()
    passed, total, results = tester.run_all_tests()
    
    # Return results for programmatic access
    return {
        "passed": passed,
        "total": total,
        "success_rate": passed / total if total > 0 else 0,
        "results": results
    }

if __name__ == "__main__":
    main()