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
  IconButton,
  Chip,
  LinearProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  Delete,
  Edit,
  PriorityHigh,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { fetchQueue, pauseDownload, resumeDownload, cancelDownload } from '../services/api';
import { formatBytes } from '../utils/formatters';

const Queue: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: queue, isLoading } = useQuery('queue', fetchQueue, {
    refetchInterval: 2000,
  });

  const pauseMutation = useMutation(pauseDownload, {
    onSuccess: () => queryClient.invalidateQueries('queue'),
  });

  const resumeMutation = useMutation(resumeDownload, {
    onSuccess: () => queryClient.invalidateQueries('queue'),
  });

  const cancelMutation = useMutation(cancelDownload, {
    onSuccess: () => queryClient.invalidateQueries('queue'),
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'downloading': return 'primary';
      case 'pending': return 'default';
      case 'paused': return 'warning';
      case 'failed': return 'error';
      case 'completed': return 'success';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'default';
      default: return 'default';
    }
  };

  if (isLoading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Download Queue
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 4 }}>
            <Box>
              <Typography variant="h6">{queue?.stats?.total || 0}</Typography>
              <Typography variant="body2" color="textSecondary">Total Items</Typography>
            </Box>
            <Box>
              <Typography variant="h6">{queue?.stats?.active || 0}</Typography>
              <Typography variant="body2" color="textSecondary">Active</Typography>
            </Box>
            <Box>
              <Typography variant="h6">{queue?.stats?.pending || 0}</Typography>
              <Typography variant="body2" color="textSecondary">Pending</Typography>
            </Box>
            <Box>
              <Typography variant="h6">{queue?.stats?.completed || 0}</Typography>
              <Typography variant="body2" color="textSecondary">Completed</Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Priority</TableCell>
                  <TableCell>Progress</TableCell>
                  <TableCell>Speed</TableCell>
                  <TableCell>ETA</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {queue?.items?.map((item: any) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
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
                        color={getStatusColor(item.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={item.priority}
                        color={getPriorityColor(item.priority) as any}
                        size="small"
                        icon={item.priority === 'high' ? <PriorityHigh /> : undefined}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ width: 100 }}>
                        <LinearProgress
                          variant="determinate"
                          value={item.progress || 0}
                        />
                        <Typography variant="caption">
                          {typeof item.progress === 'number' ? item.progress.toFixed(1) : '0'}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.speed ? formatBytes(item.speed) + '/s' : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.eta || '-'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {item.status === 'downloading' && (
                          <IconButton
                            size="small"
                            onClick={() => pauseMutation.mutate(item.id)}
                            disabled={pauseMutation.isLoading}
                          >
                            <Pause />
                          </IconButton>
                        )}
                        {item.status === 'paused' && (
                          <IconButton
                            size="small"
                            onClick={() => resumeMutation.mutate(item.id)}
                            disabled={resumeMutation.isLoading}
                          >
                            <PlayArrow />
                          </IconButton>
                        )}
                        <IconButton
                          size="small"
                          onClick={() => cancelMutation.mutate(item.id)}
                          disabled={cancelMutation.isLoading}
                          color="error"
                        >
                          <Stop />
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

export default Queue;
