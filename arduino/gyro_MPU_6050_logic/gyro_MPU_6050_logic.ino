#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

Adafruit_MPU6050 mpu;

// ---------- TUNABLE PARAMETERS ----------
#define SAMPLE_RATE_HZ      200
#define IMPACT_THRESHOLD_G  2.8
#define ANGLE_THRESHOLD_DEG 45.0
#define MOTION_THRESHOLD    0.15   // rad/s
#define INACTIVITY_TIME_MS  3000
#define IMPACT_TIMEOUT_MS   6000

// ---------- STATE MACHINE ----------
enum FallState {
  NORMAL,
  IMPACT_DETECTED,
  POST_FALL
};

FallState state = NORMAL;

// ---------- GLOBALS ----------
unsigned long lastSampleMicros = 0;
unsigned long impactTime = 0;
unsigned long stillStartTime = 0;

float pitch = 0, roll = 0;
float pitchBefore = 0, rollBefore = 0;

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  Wire.begin();

  if (!mpu.begin()) {
    Serial.println("MPU6050 not found!");
    while (1);
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  Serial.println("Fall detection ready");
}

// ---------- MAIN LOOP ----------
void loop() {
  if (micros() - lastSampleMicros < (1000000 / SAMPLE_RATE_HZ))
    return;

  lastSampleMicros = micros();

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // ---- Compute acceleration magnitude (g) ----
  float accelMag = sqrt(
    a.acceleration.x * a.acceleration.x +
    a.acceleration.y * a.acceleration.y +
    a.acceleration.z * a.acceleration.z
  ) / 9.81;

  // ---- Gyro magnitude ----
  float gyroMag =
    abs(g.gyro.x) +
    abs(g.gyro.y) +
    abs(g.gyro.z);

  // ---- Compute pitch & roll (accelerometer) ----
  float pitchAcc = atan2(
    a.acceleration.x,
    sqrt(a.acceleration.y * a.acceleration.y +
         a.acceleration.z * a.acceleration.z)
  ) * 57.2958;

  float rollAcc = atan2(
    a.acceleration.y,
    a.acceleration.z
  ) * 57.2958;

  // ---- Complementary filter ----
  static unsigned long lastTime = micros();
  float dt = (micros() - lastTime) / 1000000.0;
  lastTime = micros();

  pitch = 0.98 * (pitch + g.gyro.y * dt * 57.2958) + 0.02 * pitchAcc;
  roll  = 0.98 * (roll  + g.gyro.x * dt * 57.2958) + 0.02 * rollAcc;

  // ---- STATE MACHINE ----
  switch (state) {

    case NORMAL:
      if (accelMag > IMPACT_THRESHOLD_G) {
        impactTime = millis();
        pitchBefore = pitch;
        rollBefore = roll;
        state = IMPACT_DETECTED;
        Serial.println("IMPACT detected");
      }
      break;

    case IMPACT_DETECTED:
      if (abs(pitch - pitchBefore) > ANGLE_THRESHOLD_DEG ||
          abs(roll  - rollBefore)  > ANGLE_THRESHOLD_DEG) {

        if (gyroMag < MOTION_THRESHOLD) {
          if (stillStartTime == 0)
            stillStartTime = millis();

          if (millis() - stillStartTime > INACTIVITY_TIME_MS) {
            triggerFall();
            state = POST_FALL;
          }
        } else {
          stillStartTime = 0;
        }
      }

      if (millis() - impactTime > IMPACT_TIMEOUT_MS) {
        state = NORMAL;
        stillStartTime = 0;
      }
      break;

    case POST_FALL:
      // Wait until movement resumes
      if (gyroMag > MOTION_THRESHOLD * 2) {
        state = NORMAL;
        stillStartTime = 0;
      }
      break;
  }
}

// ---------- FALL EVENT ----------
void triggerFall() {
  Serial.println("!!! FALL DETECTED !!!");
}
