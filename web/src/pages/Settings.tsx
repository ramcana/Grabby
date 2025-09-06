import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Grid,
  Alert,
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { fetchSettings, updateSettings } from '../services/api';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery('settings', fetchSettings);

  const updateMutation = useMutation(updateSettings, {
    onSuccess: () => {
      queryClient.invalidateQueries('settings');
    },
  });

  const handleSave = () => {
    if (settings) {
      updateMutation.mutate(settings);
    }
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      {updateMutation.isSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Settings saved successfully!
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Download Settings
              </Typography>
              
              <TextField
                fullWidth
                label="Default Download Path"
                value={settings?.download_path || ''}
                margin="normal"
              />
              
              <TextField
                fullWidth
                label="Max Concurrent Downloads"
                type="number"
                value={settings?.max_concurrent || 3}
                margin="normal"
              />
              
              <FormControlLabel
                control={<Switch checked={settings?.auto_extract_audio || false} />}
                label="Auto-extract audio"
              />
              
              <FormControlLabel
                control={<Switch checked={settings?.download_subtitles || false} />}
                label="Download subtitles"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Interface Settings
              </Typography>
              
              <FormControlLabel
                control={<Switch checked={settings?.dark_mode || true} />}
                label="Dark mode"
              />
              
              <FormControlLabel
                control={<Switch checked={settings?.notifications || true} />}
                label="Show notifications"
              />
              
              <FormControlLabel
                control={<Switch checked={settings?.auto_refresh || true} />}
                label="Auto-refresh data"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Advanced Settings
              </Typography>
              
              <TextField
                fullWidth
                label="API Base URL"
                value={settings?.api_url || 'http://localhost:8000'}
                margin="normal"
              />
              
              <TextField
                fullWidth
                label="WebSocket URL"
                value={settings?.websocket_url || 'ws://localhost:8000'}
                margin="normal"
              />
              
              <Divider sx={{ my: 2 }} />
              
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSave}
                disabled={updateMutation.isLoading}
              >
                {updateMutation.isLoading ? 'Saving...' : 'Save Settings'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Settings;
