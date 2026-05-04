'use strict';

async function markSeen(matchId) {
  try {
    await fetch(`/api/matches/${matchId}/seen`, {
      method: 'PATCH',
      credentials: 'include',
    });
  } catch (_) {}
}
