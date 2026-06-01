from input_parser import fuzzy_match_region
from main import baseline

matched, score, action = fuzzy_match_region("jakarte", list(baseline.keys()))
print(f"matched: {matched}, score: {score:.1f}, action: {action}")

matched2, score2, action2 = fuzzy_match_region("antartika", list(baseline.keys()))
print(f"matched: {matched2}, score: {score2:.1f}, action: {action2}")