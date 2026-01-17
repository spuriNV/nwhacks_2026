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
  Serial.begin(115200);

  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);

    digitalWrite(trigPins[i], LOW);
    //analogWrite(motorPins[i], 0);
    digitalWrite(BUZZER_PIN, LOW);
  }
  //pinMode(motorPins[0], OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // start OFF
}

void loop() {



    long distance = getDistanceCM(trigPins[i], echoPins[i]);
    int level = getVibrationLevel(distance);

    //analogWrite(motorPins[i], vibrationPWM[level]);
    //correct one for vibration
}

long getDistanceCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return -1;

  return duration * 0.034 / 2;
}

int getVibrationLevel(long distance) {
  if (distance == -1 || distance > 100) return 0;
  else if (distance > 66) return 1;
  else if (distance > 33) return 2;
  else return 3;
}

}
