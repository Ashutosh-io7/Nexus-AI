export function formatMoney(value) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    dateStyle: 'medium',
  })
}

// "churned" is a past outcome from the customer's own data, not a prediction.
// An empty value means unknown, which is different from "stayed".
export function outcomeLabel(churned) {
  if (churned === true) return 'Left'
  if (churned === false) return 'Stayed'
  return 'Unknown'
}