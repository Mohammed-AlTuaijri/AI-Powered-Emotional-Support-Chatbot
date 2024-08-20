import React, { useState, useRef, useEffect } from 'react';
import { createTheme, ThemeProvider, CssBaseline, TextField, Button, Card, CardContent, Typography, Box, Grid, Container, Switch, IconButton } from '@mui/material';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';

function App() {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState([]);
  const [darkMode, setDarkMode] = useState(false);
  const eventSourceRef = useRef(null);
  const endOfPageRef = useRef(null);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: darkMode ? '#90caf9' : '#1976d2',
      },
      secondary: {
        main: darkMode ? '#66bb6a' : '#43a047',
      },
      queryBackground: {
        main: darkMode ? '#424242' : '#e3f2fd',
      },
    },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            transition: '0.3s',
            '&:hover': {
              transform: 'scale(1.03)',
              boxShadow: '0 8px 16px 0 rgba(0,0,0,0.2)',
            },
            borderRadius: '15px',
          }
        }
      }
    }
  });

  const scrollToBottom = () => {
    endOfPageRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleQuery = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;

    const newEntry = {
      query: query,
      responses: {}
    };
    setHistory(prev => [...prev, newEntry]);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: query })
      });

      const result = await response.json();
      console.log('Backend Response:', result);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setHistory(prev => prev.map(item =>
        item.query === query ? {...item, responses: { 'Model Response': result.response }} : item
      ));

      scrollToBottom();
    } catch (error) {
      console.error('Request failed:', error);
    }

    setQuery('');
};



  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom textAlign="center">
            Multi-Model Evaluation
          </Typography>
          {history.map((item, index) => (
            <Box key={index} sx={{ mt: 2 }}>
              <Typography variant="subtitle1" gutterBottom component="div" sx={{ color: theme.palette.secondary.main }}>
                Query: {item.query}
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(item.responses).map(([model, response], idx) => (
                  <Grid item xs={3} key={idx}>  {/* Adjust grid sizing to fit all in one line */}
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          {model.toUpperCase()} Response
                        </Typography>
                        <Typography variant="body2">
                          {typeof response === 'object' && response.error ? response.error : response}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))}
          <div ref={endOfPageRef} />
        </Box>
        <Box sx={{ textAlign: 'center', p: 2, borderTop: '1px solid #ccc', position: 'relative' }}>
          <form onSubmit={handleQuery}>
            <TextField
              fullWidth
              label="Enter your query here"
              variant="outlined"
              value={query}
              autoComplete="off"
              onChange={e => setQuery(e.target.value)}
              sx={{ mb: 2, backgroundColor: theme.palette.queryBackground.main }}
            />
            <Button type="submit" variant="contained" color="primary">
              Submit
            </Button>
            <Switch
              checked={darkMode}
              onChange={() => setDarkMode(!darkMode)}
              inputProps={{ 'aria-label': 'controlled' }}
              sx={{ ml: 2 }}
            />
          </form>
          <IconButton onClick={scrollToBottom} sx={{ position: 'fixed', bottom: 16, right: 16, backgroundColor: theme.palette.primary.main, color: theme.palette.getContrastText(theme.palette.primary.main) }}>
            <ArrowDownwardIcon />
          </IconButton>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;

