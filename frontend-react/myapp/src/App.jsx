import React from 'react';
import WebSocketClient from './components/WebSocketClient';

const App = () => {
    return (
        <div style={{ padding: '20px' }}>
            <h1>WebSocket Client Application</h1>
            <WebSocketClient />
        </div>
    );
};

export default App;
