# E13 v2: Repeat the same photo scenarios after fixing analysis failure handling

Registered after E13 v1 completed 1/3 scenarios, with two validation errors after all four calls had been attempted. Preserve v1 unchanged. The v1 fallback was missing required fields, so an analyst failure could discard successful capture and solving.

Fix the fallback's schema completeness and give the analyst an analysis-only flat schema; source fields are supplied by code from the capture result. Repeat all three identical image scenarios, without source, crop, key or model changes. Maximum twelve logical calls, no retries. Record completed analyses, source matches, answer matches, detailed-analysis availability and evidence contracts separately. This is an engineering repair evaluation, not a controlled accuracy-improvement claim or a new independent benchmark. Apply the same interpretation limits as v1.
