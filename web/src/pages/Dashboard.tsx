import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Download,
  Queue,
  CheckCircle,
  Error,
  Speed,
  Storage,
  Refresh,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { useWebSocket } from '../contexts/WebSocketContext';
import DownloadForm from '../components/DownloadForm';
import RecentDownloads from '../components/RecentDownloads';
import { fetchStats } from '../services/api';

const Dashboard: React.FC = () => {
  const { queueStatus } = useWebSocket();
  const { data: stats, refetch } = useQuery('stats', fetchStats, {
    refetchInterval: 5000,
  });

  const statCards = [
    {
      title: 'Active Downloads',
      value: queueStatus?.active_downloads || 0,
      icon: <Download />,
      color: 'primary',
    },
    {
      title: 'Queued',
      value: queueStatus?.queued || 0,
      icon: <Queue />,
      color: 'warning',
    },
    {
      title: 'Completed Today',
      value: stats?.completed_today || 0,
      icon: <CheckCircle />,
      color: 'success',
    },
    {
      title: 'Failed',
      value: stats?.failed || 0,
      icon: <Error />,
      color: 'error',
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <IconButton onClick={() => refetch()}>
          <Refresh />
        </IconButton>
      </Box>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        {statCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="textSecondary" gutterBottom variant="overline">
                      {stat.title}
                    </Typography>
                    <Typography variant="h4">
                      {stat.value}
                    </Typography>
                  </Box>
                  <Box sx={{ color: `${stat.color}.main` }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* Download Form */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Add New Download
              </Typography>
              <DownloadForm />
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">CPU Usage</Typography>
                  <Typography variant="body2">{stats?.cpu_usage || 0}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={stats?.cpu_usage || 0} />
              </Box>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Memory Usage</Typography>
                  <Typography variant="body2">{stats?.memory_usage || 0}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={stats?.memory_usage || 0} />
              </Box>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip
                  icon={<Speed />}
                  label={`${stats?.download_speed || '0 B/s'}`}
                  size="small"
                />
                <Chip
                  icon={<Storage />}
                  label={`${stats?.disk_usage || '0 GB'} used`}
                  size="small"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Downloads */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Downloads
              </Typography>
              <RecentDownloads />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
