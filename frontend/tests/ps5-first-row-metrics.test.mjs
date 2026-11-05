/** Verify first-row comparisons without inventing historical data. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compareGamingSeconds,
  aggregateDays,
  formatSessionCount,
} from '../services/ps5-first-row-metrics.js';

test('comparison shows the correct increase', () => {
  assert.deepEqual(compareGamingSeconds(7200, 3600, 'ontem'), {
    text: '▲ +100% vs. ontem', trend: 'up',
  });
});
test('comparison shows a decrease', () => {
  assert.equal(compareGamingSeconds(1800, 3600, 'ontem').trend, 'down');
});
test('zero baseline is not reported as a percentage', () => {
  assert.equal(compareGamingSeconds(3600, 0, 'ontem').text, 'Sem atividade ontem');
  assert.equal(compareGamingSeconds(0, 0, 'ontem').trend, 'neutral');
});
test('missing baseline is not assumed to be zero', () => {
  assert.equal(compareGamingSeconds(3600, null, 'ontem').trend, 'unknown');
});
test('daily aggregates sum confirmed sessions and gaming', () => {
  assert.deepEqual(aggregateDays([
    { gaming_seconds: 300, gaming_sessions: 1 },
    { gaming_seconds: 500, gaming_sessions: 2 },
  ]), { gaming_seconds: 800, gaming_sessions: 3 });
});
test('sessions display singular and plural correctly', () => {
  assert.equal(formatSessionCount(1), '1 sessão');
  assert.equal(formatSessionCount(8), '8 sessões');
  assert.equal(formatSessionCount(null), 'Sessões indisponíveis');
});
