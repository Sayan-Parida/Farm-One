from ml.advisory_llm import generate_advice

def main():
    weather = {"temp_min": 20, "temp_max": 30, "humidity": 70, "rain_7d": 0}
    soil = {"ph": 6.5, "organic_carbon_pct": 0.5}
    crop_recommendation = {"recommended_crops": []}
    yield_prediction = {"expected_yield_ton_per_hectare": 0, "confidence": "N/A"}

    print("Calling generate_advice()...")
    result = generate_advice(weather, soil, crop_recommendation, yield_prediction, question="Test advisory")
    print("Result:")
    print(result)

if __name__ == '__main__':
    main()
