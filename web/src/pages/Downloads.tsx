import React, { useState } from 'react';
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
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
  IconButton,
} from '@mui/material';
import { Download, Delete, FolderOpen } from '@mui/icons-material';
import { useQuery, useMutation } from 'react-query';
import { fetchDownloads, downloadFile, openFolder } from '../services/api';
import { formatBytes, formatTimeAgo } from '../utils/formatters';

const Downloads: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { data: downloads, isLoading } = useQuery(
    ['downloads', page, statusFilter, searchTerm],
    () => fetchDownloads({
      limit: 20,
      offset: (page - 1) * 20,
      status: statusFilter === 'all' ? undefined : statusFilter,
    }),
    { keepPreviousData: true }
  );

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

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Downloads
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              label="Search downloads"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            <FormControl sx={{ minWidth: 120 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="downloading">Downloading</MenuItem>
                <MenuItem value="failed">Failed</MenuItem>
                <MenuItem value="paused">Paused</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Quality</TableCell>
                  <TableCell>Downloaded</TableCell>
                  <TableCell>Engine</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {downloads?.items?.map((download: any) => {
                  const progress = download.progress || {};
                  const totalBytes = progress.total_bytes || 0;
                  const filename = progress.filename || download.urls?.[0] || 'Unknown';
                  const title = filename.split('/').pop()?.replace(/\.[^/.]+$/, '') || filename;
                  const quality = download.options?.format_selector || 'best';
                  
                  return (
                    <TableRow key={download.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" noWrap sx={{ maxWidth: 400 }}>
                            {title}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {download.urls?.[0]} • {formatTimeAgo(new Date(download.created_at))}
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
                        <Typography variant="body2">
                          {totalBytes ? formatBytes(totalBytes) : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {quality}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {download.completed_at ? formatTimeAgo(new Date(download.completed_at)) : '-'}
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
                          <Chip
                            label="yt-dlp"
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Pagination
              count={Math.ceil((downloads?.total || 0) / 20)}
              page={page}
              onChange={(_, newPage) => setPage(newPage)}
            />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Downloads;
