const int NUM_SENSORS = 3;

// HC-SR04 pins
int trigPins[NUM_SENSORS]  = {3, 6, 9};
int echoPins[NUM_SENSORS] = {2, 5, 8};
int cam[NUM_SENSORS] = {0, 0, 0}; // store camera data

// Vibration motor pins (PWM)
//int motorPins[NUM_SENSORS] = {11};
const int BUZZER_PIN = 11;
const int LED_PIN = 13;

// Distance thresholds (cm)
const int levelThresholds[3] = {33, 66, 100};  
const int vibrationPWM[4] = {0, 85, 170, 255};

void setup() {
  // put your setup code here, to run once:

}

void loop() {
  // put your main code here, to run repeatedly:

}
