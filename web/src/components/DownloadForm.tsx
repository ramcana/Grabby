import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Add, VideoLibrary } from '@mui/icons-material';
import { useMutation, useQueryClient } from 'react-query';
import { submitDownload, getVideoInfo } from '../services/api';
import { formatApiError } from '../utils/errorHandler';

const DownloadForm: React.FC = () => {
  const [url, setUrl] = useState('');
  const [profile, setProfile] = useState('default');
  const [quality, setQuality] = useState('best[height<=1080]');
  const [extractAudio, setExtractAudio] = useState(false);
  const [videoInfo, setVideoInfo] = useState<any>(null);
  const [error, setError] = useState('');

  const queryClient = useQueryClient();

  const downloadMutation = useMutation(submitDownload, {
    onSuccess: () => {
      setUrl('');
      setError('');
      queryClient.invalidateQueries('downloads');
      queryClient.invalidateQueries('queue');
    },
    onError: (error: any) => {
      setError(formatApiError(error));
    },
  });

  const infoMutation = useMutation(getVideoInfo, {
    onSuccess: (data) => {
      setVideoInfo(data);
      setError('');
    },
    onError: (error: any) => {
      setError(formatApiError(error));
      setVideoInfo(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    downloadMutation.mutate({
      url: url.trim(),
      profile,
      options: {
        format_selector: quality,
        extract_audio: extractAudio,
      },
    });
  };

  const handleGetInfo = () => {
    if (!url.trim()) return;
    infoMutation.mutate(url.trim());
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          fullWidth
          label="Video URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          disabled={downloadMutation.isLoading}
        />
        <Button
          variant="outlined"
          onClick={handleGetInfo}
          disabled={!url.trim() || infoMutation.isLoading}
          startIcon={infoMutation.isLoading ? <CircularProgress size={20} /> : <VideoLibrary />}
        >
          Info
        </Button>
      </Box>

      {videoInfo && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            {videoInfo.title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip label={`Duration: ${videoInfo.duration_string || 'Unknown'}`} size="small" />
            <Chip label={`Uploader: ${videoInfo.uploader || 'Unknown'}`} size="small" />
            <Chip label={`Views: ${videoInfo.view_count?.toLocaleString() || 'Unknown'}`} size="small" />
          </Box>
        </Box>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Profile</InputLabel>
          <Select
            value={profile}
            label="Profile"
            onChange={(e) => setProfile(e.target.value)}
            disabled={downloadMutation.isLoading}
          >
            <MenuItem value="default">Default</MenuItem>
            <MenuItem value="high_quality">High Quality</MenuItem>
            <MenuItem value="audio_only">Audio Only</MenuItem>
            <MenuItem value="mobile">Mobile</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Quality</InputLabel>
          <Select
            value={quality}
            label="Quality"
            onChange={(e) => setQuality(e.target.value)}
            disabled={downloadMutation.isLoading}
          >
            <MenuItem value="best">Best Available</MenuItem>
            <MenuItem value="best[height<=2160]">4K (2160p)</MenuItem>
            <MenuItem value="best[height<=1440]">2K (1440p)</MenuItem>
            <MenuItem value="best[height<=1080]">Full HD (1080p)</MenuItem>
            <MenuItem value="best[height<=720]">HD (720p)</MenuItem>
            <MenuItem value="best[height<=480]">SD (480p)</MenuItem>
            <MenuItem value="worst">Lowest Quality</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Button
        type="submit"
        variant="contained"
        disabled={!url.trim() || downloadMutation.isLoading}
        startIcon={downloadMutation.isLoading ? <CircularProgress size={20} /> : <Add />}
        fullWidth
      >
        {downloadMutation.isLoading ? 'Starting Download...' : 'Start Download'}
      </Button>
    </Box>
  );
};

export default DownloadForm;
