import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Image,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface Colorization {
  id: string;
  original_image: string;
  colorized_image: string;
  model_id: string;
  created_at: string;
}

export default function HistoryScreen() {
  const { user } = useAuth();
  const [colorizations, setColorizations] = useState<Colorization[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!user) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API_URL}/api/colorizations/${user.uid}`
      );
      setColorizations(response.data);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchHistory();
    setRefreshing(false);
  };

  const deleteItem = async (id: string) => {
    Alert.alert(
      'Delete Colorization',
      'Are you sure you want to delete this colorization?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await axios.delete(`${API_URL}/api/colorizations/${id}`);
              setColorizations(prev => prev.filter(item => item.id !== id));
            } catch (error) {
              Alert.alert('Error', 'Failed to delete colorization');
            }
          },
        },
      ]
    );
  };

  const renderItem = ({ item }: { item: Colorization }) => (
    <View style={styles.card}>
      <View style={styles.imageRow}>
        <View style={styles.imageContainer}>
          <Text style={styles.imageLabel}>Original</Text>
          <Image 
            source={{ uri: item.original_image }} 
            style={styles.thumbnail}
            resizeMode="cover"
          />
        </View>
        
        <Ionicons name="arrow-forward" size={24} color="#6366f1" />
        
        <View style={styles.imageContainer}>
          <Text style={styles.imageLabel}>Colorized</Text>
          <Image 
            source={{ uri: item.colorized_image }} 
            style={styles.thumbnail}
            resizeMode="cover"
          />
        </View>
      </View>
      
      <View style={styles.cardFooter}>
        <Text style={styles.dateText}>
          {new Date(item.created_at).toLocaleDateString()}
        </Text>
        <TouchableOpacity onPress={() => deleteItem(item.id)}>
          <Ionicons name="trash-outline" size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>
    </View>
  );

  const EmptyState = () => (
    <View style={styles.emptyState}>
      <Ionicons name="images-outline" size={64} color="#333" />
      <Text style={styles.emptyTitle}>No History Yet</Text>
      <Text style={styles.emptyText}>
        Your colorized manga pages will appear here
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>History</Text>
        <Text style={styles.subtitle}>{colorizations.length} colorizations</Text>
      </View>
      
      <FlatList
        data={colorizations}
        renderItem={renderItem}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#6366f1"
          />
        }
        ListEmptyComponent={!loading ? <EmptyState /> : null}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    padding: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
  },
  listContent: {
    padding: 24,
    paddingTop: 0,
    gap: 16,
  },
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
    gap: 16,
  },
  imageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  imageContainer: {
    flex: 1,
    gap: 8,
  },
  imageLabel: {
    fontSize: 12,
    color: '#999',
    fontWeight: '600',
  },
  thumbnail: {
    width: '100%',
    height: 120,
    borderRadius: 8,
    backgroundColor: '#0a0a0a',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  dateText: {
    fontSize: 12,
    color: '#999',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    gap: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#fff',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
});
