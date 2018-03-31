/*
 * IRremote: IRsendDemo - demonstrates sending IR codes with IRsend
 * An IR LED must be connected to Arduino PWM pin 3.
 * Version 0.1 July, 2009
 * Copyright 2009 Ken Shirriff
 * http://arcfn.com
 */


#include <IRremote.h>

IRsend irsend;

void setup()
{
  pinMode(2, INPUT);
  digitalWrite(2, HIGH);
}

void loop() {
  if(digitalRead(2) == LOW) {
    irsend.sendSony(0xa90, 12);
    delay(40);
  }
}
