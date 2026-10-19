# Sensitivität: energy_shock_sensitivity

1680 Läufe, 273 s, Code `ef7f4c696d98`. Je Variante wird eine Annahme geändert; alle Szenarien und Seeds bleiben gleich.
Absolute Größen (Importe, Staatsschuld) skalieren mit der Populationsgröße; bei den Varianten population_* sind nur Vorzeichen vergleichbar. Eine Variante mit identischen Werten wie die Basis zeigt einen Parameter, der in diesem Experiment nicht bindet.
Zellen: Median der gepaarten Differenz Szenario − S0 über die Seeds. **fett** = Vorzeichen weicht von der Basisvariante ab (Toleranz: 5 % des Basisbetrags).

## S1_transfer

| Variante | unemployment_shock | q1_real_consumption_shock | energy_burden_shock | energy_imports_shock | energy_imports_after | price_index_shock | gov_debt_change |
|---|---|---|---|---|---|---|---|
| baseline | -0.01219 | 2.69 | -0.01781 | 0.2916 | 0.041 | 0.01218 | 0.6838 |
| elasticity_low | -0.0129 | 2.695 | -0.01817 | 0.3112 | 0.028 | 0.01182 | 0.7157 |
| elasticity_high | -0.01208 | 2.387 | -0.01617 | 0.2875 | 0.054 | 0.01249 | 0.6965 |
| min_energy_share_0.4 | -0.01219 | 2.69 | -0.01781 | 0.2916 | 0.041 | 0.01218 | 0.6838 |
| wages_flexible | -0.007312 | 1.825 | -0.02481 | 0.1735 | **-0.0155** | 0.02313 | 0.6749 |
| wages_rigid | -0.01331 | 2.631 | -0.01606 | 0.3194 | 0.2015 | 0.0102 | 0.6322 |
| search_rate_0.3 | -0.01579 | 3.194 | -0.01496 | 0.3763 | 0.4155 | 0.007396 | 0.6098 |
| search_rate_0.7 | -0.008875 | 2.041 | -0.0211 | 0.2087 | **-0.0535** | 0.01704 | 0.7098 |
| low_household_wealth | -0.02294 | 5.178 | -0.0301 | 0.548 | 0.1415 | 0.007687 | 0.6955 |
| row_recycling_0.2 | -0.01437 | 3.085 | -0.01646 | 0.3444 | 0.053 | 0.01132 | 0.6819 |
| protocol_random_queue | -0.01223 | 2.782 | -0.01717 | 0.2935 | 0.0755 | 0.01228 | 0.676 |
| partners_k2 | -0.01025 | 2.083 | -0.01717 | 0.2446 | **-0.023** | 0.01661 | 0.6621 |
| population_250 | -0.01333 | 2.825 | -0.01533 | 0.08076 | 0.0615 | 0.01009 | 0.1512 |
| population_4000 | -0.01018 | 2.263 | -0.02008 | 0.9709 | **-0.123** | 0.01632 | 2.82 |

Vorzeichen robust über alle Varianten: unemployment_shock: ja, q1_real_consumption_shock: ja, energy_burden_shock: ja, energy_imports_shock: ja, energy_imports_after: nein, price_index_shock: ja, gov_debt_change: ja

## S2_subsidy

| Variante | unemployment_shock | q1_real_consumption_shock | energy_burden_shock | energy_imports_shock | energy_imports_after | price_index_shock | gov_debt_change |
|---|---|---|---|---|---|---|---|
| baseline | -0.01208 | 2.361 | -0.1285 | 0.8008 | 0.062 | 0.01148 | 0.6682 |
| elasticity_low | -0.01206 | 2.272 | -0.1422 | 0.4742 | 0.061 | 0.01234 | 0.6751 |
| elasticity_high | -0.01115 | 1.904 | -0.1084 | 1.249 | 0.055 | 0.01032 | 0.6715 |
| min_energy_share_0.4 | -0.01208 | 2.361 | -0.1285 | 0.8008 | 0.062 | 0.01148 | 0.6682 |
| wages_flexible | -0.007333 | 1.378 | -0.1544 | 0.6792 | **-0.0155** | 0.02194 | 0.669 |
| wages_rigid | -0.01215 | 2.361 | -0.1257 | 0.7998 | 0.2 | 0.009319 | 0.6308 |
| search_rate_0.3 | -0.01498 | 2.797 | -0.1255 | 0.8628 | 0.414 | 0.006381 | 0.6048 |
| search_rate_0.7 | -0.007771 | 1.484 | -0.1347 | 0.6984 | **-0.058** | 0.01842 | 0.6811 |
| low_household_wealth | -0.02187 | 4.218 | -0.1981 | 1.048 | 0.144 | 0.007209 | 0.6753 |
| row_recycling_0.2 | -0.01333 | 2.426 | -0.1288 | 0.8308 | 0.086 | 0.01042 | 0.7027 |
| protocol_random_queue | -0.01173 | 2.199 | -0.1254 | 0.7925 | 0.089 | 0.01189 | 0.6587 |
| partners_k2 | -0.01031 | 1.655 | -0.1269 | 0.756 | **-0.0335** | 0.01534 | 0.6551 |
| population_250 | -0.01458 | 2.167 | -0.1088 | 0.2123 | 0.051 | 0.009922 | 0.1474 |
| population_4000 | -0.009807 | 2.006 | -0.1319 | 2.959 | **-0.095** | 0.01508 | 2.715 |

Vorzeichen robust über alle Varianten: unemployment_shock: ja, q1_real_consumption_shock: ja, energy_burden_shock: ja, energy_imports_shock: ja, energy_imports_after: nein, price_index_shock: ja, gov_debt_change: ja

## S3_investment

| Variante | unemployment_shock | q1_real_consumption_shock | energy_burden_shock | energy_imports_shock | energy_imports_after | price_index_shock | gov_debt_change |
|---|---|---|---|---|---|---|---|
| baseline | -0.01469 | -1.167 | -0.007 | -0.01963 | -1.672 | 0.01362 | 0.6653 |
| elasticity_low | -0.01552 | -1.049 | -0.005833 | -0.01421 | -1.674 | 0.01564 | 0.6696 |
| elasticity_high | -0.01465 | -1.391 | -0.007354 | -0.01394 | -1.688 | 0.01407 | 0.6969 |
| min_energy_share_0.4 | -0.01469 | -1.167 | -0.007 | -0.01963 | -1.672 | 0.01362 | 0.6653 |
| wages_flexible | -0.009521 | -2.822 | -0.01083 | -0.1476 | -1.734 | 0.02832 | 0.6469 |
| wages_rigid | -0.01598 | -1.158 | -0.005104 | -0.0063 | -1.549 | 0.01181 | 0.5901 |
| search_rate_0.3 | -0.01919 | -0.385 | -0.006792 | **0.07478** | -1.322 | 0.007678 | 0.6205 |
| search_rate_0.7 | -0.01002 | -2.342 | -0.01079 | -0.1511 | -1.808 | 0.0206 | 0.6639 |
| low_household_wealth | -0.02708 | **-0.03102** | -0.0109 | **0.2679** | -1.614 | 0.009498 | 0.6922 |
| row_recycling_0.2 | -0.01746 | -0.6029 | -0.006542 | **0.03017** | -1.673 | 0.01208 | 0.6673 |
| protocol_random_queue | -0.01531 | -0.7042 | -0.006521 | -0.01868 | -1.649 | 0.01288 | 0.6389 |
| partners_k2 | -0.01321 | -1.909 | -0.007333 | -0.06868 | -1.779 | 0.01895 | 0.6551 |
| population_250 | -0.01575 | -0.4561 | -0.007917 | **0.00671** | -0.3517 | 0.01158 | 0.1568 |
| population_4000 | -0.01258 | -1.516 | -0.008151 | -0.3254 | -7.102 | 0.01768 | 2.766 |

Vorzeichen robust über alle Varianten: unemployment_shock: ja, q1_real_consumption_shock: nein, energy_burden_shock: ja, energy_imports_shock: nein, energy_imports_after: ja, price_index_shock: ja, gov_debt_change: ja
