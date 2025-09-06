import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  LinearProgress,
  Box,
  Typography,
} from '@mui/material';
import { PlayArrow, Pause, Stop, Refresh, Download, FolderOpen } from '@mui/icons-material';
import { useQuery, useMutation } from 'react-query';
import { fetchRecentDownloads, downloadFile, openFolder } from '../services/api';
import { formatBytes, formatDuration } from '../utils/formatters';

const RecentDownloads: React.FC = () => {
  const { data: downloads, isLoading } = useQuery('recentDownloads', fetchRecentDownloads, {
    refetchInterval: 2000,
  });

  const openFolderMutation = useMutation(openFolder, {
    onSuccess: () => {
      // Folder opened successfully
    },
    onError: (error: any) => {
      console.error('Failed to open folder:', error);
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'downloading': return 'primary';
      case 'failed': return 'error';
      case 'paused': return 'warning';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'downloading': return <Pause />;
      case 'paused': return <PlayArrow />;
      default: return <Stop />;
    }
  };

  if (isLoading) {
    return <LinearProgress />;
  }

  return (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Title</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Progress</TableCell>
            <TableCell>Speed</TableCell>
            <TableCell>Size</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {downloads?.items?.map((download: any) => {
            const progress = download.progress || {};
            const progressPercent = progress.progress_percent || 0;
            const speed = progress.speed ? progress.speed.replace(/\x1b\[[0-9;]*m/g, '') : null; // Remove ANSI color codes
            const totalBytes = progress.total_bytes || 0;
            const filename = progress.filename || download.urls?.[0] || 'Unknown';
            const title = filename.split('/').pop()?.replace(/\.[^/.]+$/, '') || filename;
            
            return (
              <TableRow key={download.id}>
                <TableCell>
                  <Box>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {title}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {download.urls?.[0]}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={download.status}
                    color={getStatusColor(download.status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ width: 100 }}>
                    <LinearProgress
                      variant="determinate"
                      value={progressPercent}
                    />
                    <Typography variant="caption">
                      {typeof progressPercent === 'number' ? progressPercent.toFixed(1) : '0'}%
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {speed || '-'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {totalBytes ? formatBytes(totalBytes) : '-'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {download.status === 'completed' && (
                      <>
                        <IconButton 
                          size="small" 
                          onClick={() => downloadFile(download.id)}
                          title="Download file"
                        >
                          <Download />
                        </IconButton>
                        <IconButton 
                          size="small" 
                          onClick={() => openFolderMutation.mutate(download.id)}
                          disabled={openFolderMutation.isLoading}
                          title="Open folder"
                        >
                          <FolderOpen />
                        </IconButton>
                      </>
                    )}
                    {download.status !== 'completed' && (
                      <IconButton size="small">
                        {getStatusIcon(download.status)}
                      </IconButton>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default RecentDownloads;
