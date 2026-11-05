import test from 'node:test';
import assert from 'node:assert/strict';
import { PS5LiveClient, validateLiveState, LIVE_TOPIC } from '../services/ps5-live-client.js';
const payload = (generation = 1) => ({ schema_version: 1, power: 'AWAKE', activity: 'playing', console_active: true, player_gaming: true, available: true, observed_at: new Date().toISOString(), title_id: 'PPSA17221_00', title_name: 'Minecraft', generation });
function fixture() {
  const subscriptions = [];
  let releases = 0;
  const hass = { connection: { async subscribeMessage(callback, options) { subscriptions.push({callback,options}); return () => { releases++; }; } } };
  return {hass,subscriptions,get releases(){return releases;}};
}
test('validates the observed playing state', () => { assert.equal(validateLiveState(payload()).title_name, 'Minecraft'); });
test('rejects malformed state', () => { assert.throws(() => validateLiveState({}), /Invalid/); });
test('subscribes to the dedicated live topic', async () => { const f=fixture(); const client=new PS5LiveClient(f.hass,()=>{}); await client.connect(); assert.equal(f.subscriptions[0].options.topic,LIVE_TOPIC); client.dispose(); });
test('accepts live updates and rejects older generations', async () => { const f=fixture(); const values=[]; const client=new PS5LiveClient(f.hass, v=>values.push(v)); await client.connect(); f.subscriptions[0].callback({topic:LIVE_TOPIC,payload:JSON.stringify(payload(2))}); f.subscriptions[0].callback({topic:LIVE_TOPIC,payload:JSON.stringify(payload(1))}); assert.equal(values.length,1); client.dispose(); });
test('releases subscription on disposal', async () => { const f=fixture(); const client=new PS5LiveClient(f.hass,()=>{}); await client.connect(); client.dispose(); assert.equal(f.releases,1); });
test('resubscribes after connection replacement', async () => { const a=fixture(),b=fixture(); const client=new PS5LiveClient(a.hass,()=>{}); await client.connect(); client.updateHass(b.hass); assert.equal(a.releases,1); await client.connect(); assert.equal(b.subscriptions.length,1); client.dispose(); });
