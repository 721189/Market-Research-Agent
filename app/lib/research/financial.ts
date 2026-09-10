export function calculateUnitEconomics(baseCogs: number, targetMarginPercentage: number) {
  // Ensure we don't divide by zero or negative margin
  const safeMargin = Math.min(Math.max(targetMarginPercentage, 1), 99);
  
  // Price = COGS / (1 - margin)
  const retailPrice = baseCogs / (1 - (safeMargin / 100));
  const grossMargin = retailPrice - baseCogs;
  
  return {
    estimatedCogs: Number(baseCogs.toFixed(2)),
    suggestedRetailPrice: Number(retailPrice.toFixed(2)),
    projectedMarginPercentage: safeMargin,
    grossMarginDollars: Number(grossMargin.toFixed(2))
  };
}
