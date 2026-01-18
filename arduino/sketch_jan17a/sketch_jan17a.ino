const int NUM_SENSORS = 3;

// HC-SR04 pins
int trigPins[NUM_SENSORS]  = {13, 8, 4};//8
int echoPins[NUM_SENSORS] = {12, 7, 2};//7
int cam[NUM_SENSORS] = {0, 0, 0}; // store camera data


// Vibration motor pins (PWM)
int motorPins[NUM_SENSORS] = {11, 9, 3};

// Distance thresholds (cm)
const int levelThresholds[] = {33, 66, 100};  
const int vibrationPWM[4] = {0, 130, 175, 255};

int obj[NUM_SENSORS] = {0, 0, 0};  // YOLO object flags
int vibrationEnabled = 1;     // enable / disable
int vibrationPattern = 0;         // pattern index


void setup() {
  Serial.begin(115200);

  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);

    digitalWrite(trigPins[i], LOW);
    analogWrite(motorPins[i], 0);
    // digitalWrite(BUZZER_PIN, LOW);
  }
  //pinMode(motorPins[0], OUTPUT);

}

void loop() {

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    parseSerialCommand(line);
  }

  int distances[NUM_SENSORS] = {0, 0, 0};
  int vibeLevels[NUM_SENSORS] = {0, 0, 0}; 

  for (int i = 0; i < NUM_SENSORS; i++) {
    //first 3 = object boolean from yolo
    //next 3 enable/disable vibration motors(0 or 1, boolean), vibration pattern(0-3) - integer
    //[obj 1, obj 2, obj 3, enable/disable, vibration pattern]
    long distance = getDistanceCM(trigPins[i], echoPins[i]);
    int level = getVibrationLevel(distance);

    distances[i] = distance;
    vibeLevels[i] = level;

    if (vibrationEnabled && obj[i] && level > 0) {
      applyVibrationPattern(
        motorPins[i],
        vibrationPWM[level],
        vibrationPattern
      );
    } else {
      analogWrite(motorPins[i], 0);
    }

    

    delay(60); // prevent ultrasonic crosstalk
  }


  Serial.println("--------------------");
  for (int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(distances[i]);
    Serial.print(",");
  }

  for (int i = 0; i < NUM_SENSORS; i++) {
    Serial.print(vibeLevels[i]);
    Serial.print(",");
  }

  Serial.println();

  delay(1000); // helps reduce ultrasonic interference
}

// -------------------- FUNCTIONS --------------------

void parseSerialCommand(String line) {
  int values[5];
  int index = 0;
  int lastPos = 0;

  for (int i = 0; i < line.length() && index < 5; i++) {
    if (line.charAt(i) == ',' || i == line.length() - 1) {
      values[index++] = line.substring(lastPos, i + 1).toInt();
      lastPos = i + 1;
    }
  }

  if (index == 5) {
    for (int i = 0; i < NUM_SENSORS; i++) {
      obj[i] = values[i];
    }
    vibrationEnabled = values[3];
    vibrationPattern = constrain(values[4], 0, 3);
  }
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

// ----- All Vibration Patterns -----
void applyVibrationPattern(int motorPin, int pwm, int pattern) {
  switch (pattern) {

    // Pattern 0: Continuous (distance-controlled)
    case 0:
      analogWrite(motorPin, pwm);
      break;

    // Pattern 1: Heartbeat (thump...pause)
    case 1:
      analogWrite(motorPin, pwm);
      delay(80);
      analogWrite(motorPin, 0);
      delay(200);
      break;

    // Pattern 2: Rapid pulse (urgent)
    case 2:
      analogWrite(motorPin, pwm);
      delay(40);
      analogWrite(motorPin, 0);
      delay(40);
      break;

    // Pattern 3: Double tap (distinct signal)
    case 3:
      analogWrite(motorPin, pwm);
      delay(50);
      analogWrite(motorPin, 0);
      delay(50);
      analogWrite(motorPin, pwm);
      delay(50);
      analogWrite(motorPin, 0);
      delay(200);
      break;
  }
}
