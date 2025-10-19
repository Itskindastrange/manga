import { Stack } from 'expo-router';
import { AuthProvider } from '../contexts/AuthContext';
import React from 'react';

export default function RootLayout() {
  return (
    <AuthProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)/login" />
        <Stack.Screen name="(auth)/signup" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </AuthProvider>
  );
}
