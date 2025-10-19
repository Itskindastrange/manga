import { initializeApp, getApps } from 'firebase/app';
import { getAuth, initializeAuth, getReactNativePersistence } from 'firebase/auth';
import { getStorage } from 'firebase/storage';
import AsyncStorage from '@react-native-async-storage/async-storage';

const firebaseConfig = {
  apiKey: "AIzaSyAvEp85hsqdfpMBIWOwibW3Ex4Xgilb5E0",
  authDomain: "manga-emergent.firebaseapp.com",
  projectId: "manga-emergent",
  storageBucket: "manga-emergent.firebasestorage.app",
  messagingSenderId: "949674759639",
  appId: "1:949674759639:web:ee09aa998baf6cc01f2792",
  measurementId: "G-VX3NW8Y96H"
};

// Initialize Firebase
let app;
if (getApps().length === 0) {
  app = initializeApp(firebaseConfig);
} else {
  app = getApps()[0];
}

// Initialize Auth with persistence
let auth;
try {
  auth = initializeAuth(app, {
    persistence: getReactNativePersistence(AsyncStorage)
  });
} catch (error) {
  // Auth already initialized
  auth = getAuth(app);
}

// Initialize Storage
const storage = getStorage(app);

export { app, auth, storage };
