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
  // for (int i = 0; i < NUM_SENSORS; i++) {
  //   if (Serial.available() > 0) {
  //   String data = Serial.readStringUntil('\n'); // read a line
  //   Serial.print("Received: ");
  //   Serial.println(data);

    // Turn on LED for 500ms to indicate data receive
  // }

  for (int i = 0; i < NUM_SENSORS; i++) {

    long distance = getDistanceCM(trigPins[i], echoPins[i]);
    int level = getVibrationLevel(distance);

    Serial.print("Sensor ");
    Serial.print(i);
    Serial.print(": Distance=");
    Serial.print(distance);
    Serial.print(" cm | Level=");
    Serial.println(level);

    analogWrite(motorPins[i], vibrationPWM[level]);
    

    delay(60); // prevent ultrasonic crosstalk
  }

    // long distance = getDistanceCM(trigPins[i], echoPins[i]);
    // int level = getVibrationLevel(distance);

    //analogWrite(motorPins[i], vibrationPWM[level]);
    //correct one for vibration

    // testing range
    // if (i == 0 && distance <= 20 && distance >= 0){
    //   analogWrite(BUZZER_PIN, 50);
    //   delay(800);
    //   analogWrite(BUZZER_PIN, 0);
    // }

    // Debug output
    // Serial.print("Sensor ");
    // Serial.print(i);
    // Serial.print(": Distance=");
    // Serial.print(distance);
    // Serial.print(" cm | Level=");
    // Serial.println(level);
    // if (Serial.available()) {
    //   String data = Serial.readStringUntil('\n'); // read one line
    //   parseCameraData(data, cam);                 // fill cam[] array
    // }

    // // Debug cam print
    // for (int i = 0; i < NUM_SENSORS; i++) {
    //   Serial.print("Camera "); 
    //   Serial.print(i); 
    //   Serial.print(": "); 
    //   Serial.println(cam[i]);
    // }
  // }

  Serial.println("--------------------");
  delay(1000); // helps reduce ultrasonic interference
}

// -------------------- FUNCTIONS --------------------

// Parses a string like "1,0,1" into cam[] array
// void parseCameraData(String data, int cam[]) {
//   int lastIndex = 0;
//   for (int i = 0; i < NUM_SENSORS; i++) {
//     int commaIndex = data.indexOf(',', lastIndex);
//     String value;
//     if (commaIndex == -1) { 
//       value = data.substring(lastIndex); // last value
//     } else {
//       value = data.substring(lastIndex, commaIndex);
//     }
//     cam[i] = value.toInt();
//     lastIndex = commaIndex + 1;
//   }
// }

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
