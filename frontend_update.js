const BACKEND_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? 'http://localhost:8426'
  : 'https://pirates.opencodingsociety.com';

    const r = await fetch(`${BACKEND_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: history  // Backend adds system prompt internally
      })
    });
