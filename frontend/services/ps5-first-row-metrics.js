/**
 * First-row confirmed gaming metrics and comparison helpers.
 * Never divide by zero or claim a percentage without a valid baseline.
 */
export function compareGamingSeconds(current, previous, previousLabel) {
  if (![current, previous].every(value => Number.isFinite(value) && value >= 0)) {
    return { text: 'Comparação indisponível', trend: 'unknown' };
  }
  if (previous === 0) {
    return {
      text: current === 0 ? 'Sem atividade em ambos os períodos' : `Sem atividade ${previousLabel}`,
      trend: current === 0 ? 'neutral' : 'new',
    };
  }
  const difference = current - previous;
  const percentage = Math.round(Math.abs(difference / previous) * 100);
  return {
    text: `${difference > 0 ? '▲ +' : difference < 0 ? '▼ −' : '● '}${percentage}% vs. ${previousLabel}`,
    trend: difference > 0 ? 'up' : difference < 0 ? 'down' : 'neutral',
  };
}

export function aggregateDays(days) {
  if (!Array.isArray(days)) throw new TypeError('Expected daily history array.');
  return days.reduce((total, day) => ({
    gaming_seconds: total.gaming_seconds + day.gaming_seconds,
    gaming_sessions: total.gaming_sessions + day.gaming_sessions,
  }), { gaming_seconds: 0, gaming_sessions: 0 });
}

export function formatSessionCount(value) {
  return Number.isInteger(value) && value >= 0
    ? `${value} ${value === 1 ? 'sessão' : 'sessões'}`
    : 'Sessões indisponíveis';
}
