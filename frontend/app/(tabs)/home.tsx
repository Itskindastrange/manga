import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function HomeScreen() {
  const { user } = useAuth();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [colorizedImage, setColorizedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const pickImage = async () => {
    // Request permissions
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert(
        'Permission Denied',
        'Sorry, we need camera roll permissions to upload images.'
      );
      return;
    }

    // Pick image
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      setSelectedImage(result.assets[0].uri);
      setColorizedImage(null);
    }
  };

  const colorizeImage = async () => {
    if (!selectedImage) {
      Alert.alert('No Image', 'Please select an image first');
      return;
    }

    setLoading(true);
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', {
        uri: selectedImage,
        type: 'image/jpeg',
        name: 'manga.jpg',
      } as any);
      formData.append('user_id', user?.uid || 'anonymous');
      formData.append('model_id', 'piddnad/DDColor');

      // Call API
      const response = await axios.post(
        `${API_URL}/api/colorize`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 120000, // 2 minutes
        }
      );

      if (response.data && response.data.colorized_image) {
        setColorizedImage(response.data.colorized_image);
        Alert.alert('Success', 'Your manga has been colorized!');
      }
    } catch (error: any) {
      console.error('Colorization error:', error);
      
      if (error.response) {
        // Server responded with error
        Alert.alert(
          'Colorization Failed',
          error.response.data.detail || 'Server error occurred'
        );
      } else if (error.request) {
        // Network error
        Alert.alert(
          'Network Error',
          'Could not connect to the server. Please check your internet connection.'
        );
      } else {
        Alert.alert('Error', error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setSelectedImage(null);
    setColorizedImage(null);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>Colorify Manga</Text>
          <Text style={styles.subtitle}>Upload and colorize your manga pages</Text>
        </View>

        <View style={styles.uploadSection}>
          {!selectedImage && !colorizedImage && (
            <TouchableOpacity style={styles.uploadButton} onPress={pickImage}>
              <Ionicons name="cloud-upload-outline" size={48} color="#6366f1" />
              <Text style={styles.uploadText}>Upload Manga Page</Text>
              <Text style={styles.uploadHint}>Tap to select an image</Text>
            </TouchableOpacity>
          )}

          {selectedImage && (
            <View style={styles.imageSection}>
              <Text style={styles.sectionTitle}>Original</Text>
              <Image source={{ uri: selectedImage }} style={styles.image} resizeMode="contain" />
              
              {!loading && !colorizedImage && (
                <View style={styles.actionButtons}>
                  <TouchableOpacity style={styles.primaryButton} onPress={colorizeImage}>
                    <Ionicons name="color-palette" size={20} color="#fff" />
                    <Text style={styles.primaryButtonText}>Colorize</Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity style={styles.secondaryButton} onPress={reset}>
                    <Ionicons name="close-circle" size={20} color="#999" />
                    <Text style={styles.secondaryButtonText}>Cancel</Text>
                  </TouchableOpacity>
                </View>
              )}

              {loading && (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator size="large" color="#6366f1" />
                  <Text style={styles.loadingText}>Colorizing your manga...</Text>
                  <Text style={styles.loadingHint}>This may take up to 2 minutes</Text>
                </View>
              )}
            </View>
          )}

          {colorizedImage && (
            <View style={styles.imageSection}>
              <Text style={styles.sectionTitle}>Colorized Result</Text>
              <Image 
                source={{ uri: colorizedImage }} 
                style={styles.image} 
                resizeMode="contain" 
              />
              
              <View style={styles.actionButtons}>
                <TouchableOpacity style={styles.primaryButton} onPress={reset}>
                  <Ionicons name="add-circle" size={20} color="#fff" />
                  <Text style={styles.primaryButtonText}>New Image</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#999',
  },
  uploadSection: {
    flex: 1,
  },
  uploadButton: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#333',
    borderStyle: 'dashed',
    padding: 48,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 300,
  },
  uploadText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#fff',
    marginTop: 16,
  },
  uploadHint: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  imageSection: {
    gap: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  image: {
    width: '100%',
    height: 400,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: '#6366f1',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 56,
    borderRadius: 12,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 56,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  secondaryButtonText: {
    color: '#999',
    fontSize: 16,
    fontWeight: '600',
  },
  loadingContainer: {
    alignItems: 'center',
    padding: 32,
    gap: 12,
  },
  loadingText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  loadingHint: {
    fontSize: 14,
    color: '#999',
  },
});
