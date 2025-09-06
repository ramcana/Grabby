import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
} from '@mui/material';
import { Download, Delete, FolderOpen } from '@mui/icons-material';
import { useQuery, useMutation } from 'react-query';
import { fetchHistory, downloadFile, openFolder } from '../services/api';
import { formatBytes, formatTimeAgo } from '../utils/formatters';
import { HistoryResponse } from '../types/api';

const History: React.FC = () => {
  const { data: history, isLoading } = useQuery<HistoryResponse>('history', () => fetchHistory());

  const openFolderMutation = useMutation(openFolder, {
    onSuccess: () => {
      // Folder opened successfully
    },
    onError: (error: any) => {
      console.error('Failed to open folder:', error);
    },
  });

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Download History
      </Typography>

      <Card>
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Completed</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history?.items?.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 400 }}>
                          {item.title || item.url}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {item.uploader}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={item.status}
                        color={item.status === 'completed' ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.file_size ? formatBytes(item.file_size) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.duration || '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatTimeAgo(new Date(item.completed_at))}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {item.status === 'completed' && (
                          <>
                            <IconButton 
                              size="small" 
                              onClick={() => downloadFile(item.id)}
                              title="Download file"
                            >
                              <Download />
                            </IconButton>
                            <IconButton 
                              size="small" 
                              onClick={() => openFolderMutation.mutate(item.id)}
                              disabled={openFolderMutation.isLoading}
                              title="Open folder"
                            >
                              <FolderOpen />
                            </IconButton>
                          </>
                        )}
                        <IconButton size="small" color="error" title="Delete from history">
                          <Delete />
                        </IconButton>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default History;
