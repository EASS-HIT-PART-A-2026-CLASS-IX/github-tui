const INTEGER_FORMATTER = new Intl.NumberFormat('en-US')

export function formatNumber(value) {
  return INTEGER_FORMATTER.format(Number(value || 0))
}

export function formatDate(value) {
  if (!value || value === '-') {
    return '-'
  }
  return value
}

