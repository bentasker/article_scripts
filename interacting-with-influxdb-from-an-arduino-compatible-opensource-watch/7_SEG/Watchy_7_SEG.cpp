#include "Watchy_7_SEG.h"
#include <InfluxDbClient.h>

#define DARKMODE true

// TODO: Move these to settings.h
#define INFLUXDB_URL "http://192.168.3.84:8086"
#define INFLUXDB_DB_NAME "testing_db"


// Used to read stats
#define INFLUXDB_READ_AUTH_HEADER ""
#define INFLUXDB_READ_URL "http://192.168.3.84:8086"
#define INFLUXDB_READ_DB "Systemstats"

InfluxDBClient client(INFLUXDB_URL, INFLUXDB_DB_NAME);
Point wsensor("watchy");

// We want the last cached value to be kept in the RTC's memory
// otherwise it won't survive sleeps
RTC_NOINIT_ATTR uint16_t lastEfficiency=0;


const uint8_t BATTERY_SEGMENT_WIDTH = 7;
const uint8_t BATTERY_SEGMENT_HEIGHT = 11;
const uint8_t BATTERY_SEGMENT_SPACING = 9;
const uint8_t WEATHER_ICON_WIDTH = 48;
const uint8_t WEATHER_ICON_HEIGHT = 32;

void Watchy7SEG::drawWatchFace(){

    bool minute_is_even = (currentTime.Minute % 2 == 0);

    display.fillScreen(DARKMODE ? GxEPD_BLACK : GxEPD_WHITE);
    display.setTextColor(DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    drawTime();
    drawDate();
    drawSteps();
    drawWeather(minute_is_even);
    drawBattery();
    display.drawBitmap(120, 77, WIFI_CONFIGURED ? wifi : wifioff, 26, 18, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    if(BLE_CONFIGURED){
        display.drawBitmap(100, 75, bluetooth, 13, 21, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    }

    if ((currentTime.Minute == 0 || currentTime.Minute == 30) && connectWiFi()) {
        // Trigger solar state update
        if (minute_is_even){
          getSolarState(true);
        }

        // Push stats to InfluxDB
        writeStats();

        // Turn the radios back off
        WiFi.mode(WIFI_OFF); 
        btStop();    
    } else {
        if (minute_is_even){
          getSolarState(false);
        }
    }
}

void Watchy7SEG::writeStats(){
  wsensor.clearFields();

  uint64_t chipid;

  chipid = ESP.getEfuseMac();
  String device_id = String("watchy-") + String(chipid);

  uint32_t stepCount = sensor.getCounter();
  float vbat = getBatteryVoltage();

  wsensor.addField("steps", stepCount);
  wsensor.addField("batteryvoltage", vbat);
  wsensor.addTag("device", device_id);

  // Write the point to the buffer
  client.writePoint(wsensor);

  if (!client.isBufferEmpty()) {
      // Write all remaining points to db
      client.flushBuffer();
  }
}

void Watchy7SEG::getSolarState(bool fetchState){
  bool haveValue = false;
  String suppliedString;

  // To save battery, we only actually place a HTTP request every ~6 minutes and use the
  // cached version the rest of the time
  if (fetchState){
      HTTPClient http; 
      http.setConnectTimeout(3000); // 3 second max timeout, no point burning battery

      // Add the auth header (underlying http library requires user/pass)
      // so we can't set a Bearer header
      http.setAuthorization("any", INFLUXDB_READ_AUTH_HEADER);
      
      // the library doesn't urlencode for us, so we need to supply pre-encoded query strings
      String QueryURL = INFLUXDB_READ_URL + String("/query?db=") + INFLUXDB_READ_DB + String("&q=SELECT%20round%28last%28localSupplyPercToday%3A%3Ainteger%29%29%20as%20i%20FROM%20solar_inverter%20WHERE%20time%20%3E%20now%28%29%20-%2020m");

      // Place the request
      http.begin(QueryURL.c_str());
      int httpResponseCode = http.GET();
        
      //display.print(httpResponseCode);
      if (httpResponseCode == 200) {
        String payload             = http.getString();
        JSONVar responseObject     = JSON.parse(payload);

        // This needs a double caste - JSONVar can't go straight to string if the json
        // entry wasn't itself a string
        uint16_t supplyPerc = responseObject["results"][0]["series"][0]["values"][0][1];
        suppliedString = String(supplyPerc);

        // Cache the value
        lastEfficiency = supplyPerc;
        haveValue = true;

      } else if (lastEfficiency < 1000){

          // Request failed so use the cached version
          suppliedString = String(lastEfficiency);
          haveValue = true;

      }
      // Close the HTTP object
      http.end();      
  } else {
    // Using cached version, if available
    if (lastEfficiency < 1000){
          suppliedString = String(lastEfficiency);
          haveValue = true;
    }
  }
  if (haveValue){
    // Display the value

    // The text will be right aligned, so work out where to start writing it
    int16_t  x1, y1;
    uint16_t w, h;
    display.getTextBounds(suppliedString, 0, 0, &x1, &y1, &w, &h);
    display.setCursor(159 - w - x1, 150);
    
    // Print the value
    display.println(suppliedString);

    // Draw a percent symbol
    display.drawBitmap(165, 130, percent, 26, 20, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
  }
}

void Watchy7SEG::drawTime(){
    display.setFont(&DSEG7_Classic_Bold_53);
    display.setCursor(5, 53+5);
    int displayHour;
    if(HOUR_12_24==12){
      displayHour = ((currentTime.Hour+11)%12)+1;
    } else {
      displayHour = currentTime.Hour;
    }
    if(displayHour < 10){
        display.print("0");
    }
    display.print(displayHour);
    display.print(":");
    if(currentTime.Minute < 10){
        display.print("0");
    }
    display.println(currentTime.Minute);
}

void Watchy7SEG::drawDate(){
    display.setFont(&Seven_Segment10pt7b);

    int16_t  x1, y1;
    uint16_t w, h;

    String dayOfWeek = dayStr(currentTime.Wday);
    display.getTextBounds(dayOfWeek, 5, 85, &x1, &y1, &w, &h);
    if(currentTime.Wday == 4){
        w = w - 5;
    }
    display.setCursor(85 - w, 85);
    display.println(dayOfWeek);

    String month = monthShortStr(currentTime.Month);
    display.getTextBounds(month, 60, 110, &x1, &y1, &w, &h);
    display.setCursor(85 - w, 110);
    display.println(month);

    display.setFont(&DSEG7_Classic_Bold_25);
    display.setCursor(5, 120);
    if(currentTime.Day < 10){
    display.print("0");
    }
    display.println(currentTime.Day);
    display.setCursor(5, 150);
    display.println(tmYearToCalendar(currentTime.Year));// offset from 1970, since year is stored in uint8_t
}
void Watchy7SEG::drawSteps(){
    // reset step counter at midnight
    if (currentTime.Hour == 0 && currentTime.Minute == 0){
      sensor.resetStepCounter();
    }
    uint32_t stepCount = sensor.getCounter();
    display.drawBitmap(10, 165, steps, 19, 23, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    display.setCursor(35, 190);
    display.println(stepCount);
}
void Watchy7SEG::drawBattery(){
    display.drawBitmap(154, 73, battery, 37, 21, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    display.fillRect(159, 78, 27, BATTERY_SEGMENT_HEIGHT, DARKMODE ? GxEPD_BLACK : GxEPD_WHITE);//clear battery segments
    int8_t batteryLevel = 0;
    float VBAT = getBatteryVoltage();
    if(VBAT > 4.1){
        batteryLevel = 3;
    }
    else if(VBAT > 3.95 && VBAT <= 4.1){
        batteryLevel = 2;
    }
    else if(VBAT > 3.80 && VBAT <= 3.95){
        batteryLevel = 1;
    }
    else if(VBAT <= 3.80){
        batteryLevel = 0;
    }

    for(int8_t batterySegments = 0; batterySegments < batteryLevel; batterySegments++){
        display.fillRect(159 + (batterySegments * BATTERY_SEGMENT_SPACING), 78, BATTERY_SEGMENT_WIDTH, BATTERY_SEGMENT_HEIGHT, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    }
}

void Watchy7SEG::drawWeather(bool suppressTemp){

    weatherData currentWeather = getWeatherData();

    int16_t weatherConditionCode = currentWeather.weatherConditionCode;

    // If it's an odd minute, show temperature
    // (on even minutes we'll display solar efficiency info)
    if (!suppressTemp){
        int8_t temperature = currentWeather.temperature;

        display.setFont(&DSEG7_Classic_Regular_39);
        int16_t  x1, y1;
        uint16_t w, h;
        display.getTextBounds(String(temperature), 0, 0, &x1, &y1, &w, &h);
        if(159 - w - x1 > 87){
            display.setCursor(159 - w - x1, 150);
        }else{
            display.setFont(&DSEG7_Classic_Bold_25);
            display.getTextBounds(String(temperature), 0, 0, &x1, &y1, &w, &h);
            display.setCursor(159 - w - x1, 136);
        }
        display.println(temperature);
        display.drawBitmap(165, 110, currentWeather.isMetric ? celsius : fahrenheit, 26, 20, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
    }
    const unsigned char* weatherIcon;

    //https://openweathermap.org/weather-conditions
    if(weatherConditionCode > 801){//Cloudy
    weatherIcon = cloudy;
    }else if(weatherConditionCode == 801){//Few Clouds
    weatherIcon = cloudsun;
    }else if(weatherConditionCode == 800){//Clear
    weatherIcon = sunny;
    }else if(weatherConditionCode >=700){//Atmosphere
    weatherIcon = atmosphere;
    }else if(weatherConditionCode >=600){//Snow
    weatherIcon = snow;
    }else if(weatherConditionCode >=500){//Rain
    weatherIcon = rain;
    }else if(weatherConditionCode >=300){//Drizzle
    weatherIcon = drizzle;
    }else if(weatherConditionCode >=200){//Thunderstorm
    weatherIcon = thunderstorm;
    }else
    return;
    display.drawBitmap(145, 158, weatherIcon, WEATHER_ICON_WIDTH, WEATHER_ICON_HEIGHT, DARKMODE ? GxEPD_WHITE : GxEPD_BLACK);
}
