export type ExpressionWeights = Record<string, number>;
export type ExpressionTable = Record<string, ExpressionWeights>;

/** Map a dialog expression name (x_expression) to VRM expression weights. */
export function resolveExpression(table: ExpressionTable, name: string): ExpressionWeights {
  return table[name] ?? table.neutral ?? {};
}
