# Customer panel data contract

| Default column | Meaning | Rules |
|---|---|---|
| customer_id | Customer/account identifier | Nonmissing, stable; unique with month |
| month | Analysis month index | Consecutive integer month indexes; shared balanced periods; event starts at 4 by default |
| attended | Ever-attended membership | Binary 0/1, constant within customer; NOT current exposure |
| revenue | Revenue in that month | Finite numeric; one consistent definition/currency |
| baseline_revenue | Mean revenue in separate historical window | Numeric, finite, fixed within customer |
| revenue_trend | Revenue slope per historical month | Numeric, finite, fixed within customer |
| revenue_volatility | Residual historical revenue standard deviation | Numeric, finite, fixed within customer |

The three baseline features in the example come from months -8 through -1. Analysis months are 0 through 7; event exposure begins at month 4. Real features should be built as-of a locked cutoff preceding invitations/anticipation where possible. Do not calculate the features from the full pre/post panel.

A row for zero revenue is valid if it means observed zero revenue. Do not turn missing tracking or incomplete billing into zeros. The first pipeline deliberately requires a balanced panel so attrition decisions must be made explicitly upstream. Currency conversion, refunds, repeated events, customer merges, and revenue recognition need business-specific rules.

Only numeric features are supported. Encode and document any categories upstream. Treatment timing is supplied as one shared date in configuration; the pipeline cannot verify from membership alone whether actual attendance dates were staggered. The analyst must verify the single-event design.

The input may contain extra columns, which are ignored. Do not commit source customer data, scores with real IDs, or reports containing customer records. The synthetic example is safe to share.
