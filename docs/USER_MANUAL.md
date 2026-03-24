# AgroSmart User Manual

## Login and Registration

1. Open the site in a browser.
2. Create an account using the Register page.
3. Login to access the dashboard.

## Crop Recommendation

1. Go to Dashboard -> Crop Recommendation.
2. Enter soil parameters (N, P, K, pH), weather inputs (temperature, humidity, rainfall), and season.
3. Click Predict Crop.
4. View the recommended crop and top matches.
5. Use "View history" to see saved predictions.
6. (Optional) Click "Auto-fill weather" to fill temperature/humidity/rainfall from OpenWeather (requires API key and Profile location).

### Crop Recommendation Fields

- Nitrogen (N): Soil nitrogen level from a soil test report. Used to estimate nutrient suitability for crops.
- Phosphorus (P): Soil phosphorus level from a soil test report.
- Potassium (K): Soil potassium level from a soil test report.
- Temperature (°C): Average local temperature (recent/seasonal).
- Humidity (%): Relative humidity (0-100).
- Rainfall (mm): Rainfall estimate (recent/seasonal).
- Soil pH: Soil acidity/alkalinity (0-14). Many crops perform best around pH 5.5-7.5.
- Season: Kharif/Rabi/Summer/Annual. Helps tailor crop suitability.

## Fertilizer Recommendation

1. Go to Dashboard -> Fertilizer Recommendation.
2. Enter crop name and N, P, K values.
3. Click Recommend Fertilizer.
4. View focus nutrients, a simple nutrient status chart, and usage instructions.
5. Use "View history" to see saved recommendations.

### Fertilizer Recommendation Fields

- Crop name: The crop you plan to grow (example: Rice, Tomato, Cotton).
- Nitrogen (N), Phosphorus (P), Potassium (K): Soil nutrient values from a soil test report.

## Disease Detection

1. Go to Dashboard -> Disease Detection.
2. Upload a leaf image (jpg/png).
3. Click Detect Disease.
4. View disease result, treatment, and prevention.
5. Use "View history" to see saved predictions.

## Exports

From the Dashboard, use:

- Download my history (CSV): exports your crop/fertilizer/disease history.
- Download my report (PDF): generates a simple PDF report (requires `reportlab`).

### Disease Detection Fields

- Leaf image: A clear photo of a single affected leaf. Good lighting and a close shot improves prediction.
