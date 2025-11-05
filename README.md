# Ticker

LED Matrix Display System for Sports Scores

## Overview

A Python-based LED matrix display system that shows live sports scores, team logos, and game information. Designed for LED matrix displays with optimized graphics and real-time data updates.

## Features

- **LED-Optimized Graphics**: Custom image processing pipeline for LED matrix displays
- **Live Sports Data**: Real-time scores and game information 
- **Team Logos**: Comprehensive collection of sports team logos optimized for LED display
- **Custom Fonts**: BDF font support for LED matrix displays
- **Hardware Integration**: Direct LED matrix control and display management

## Hardware Requirements

- LED Matrix Display
- Raspberry Pi or compatible controller
- Power supply suitable for LED matrix

## Directory Structure

```
ticker/
├── code.py          # Main display control code
├── fonts/           # BDF fonts for LED display
├── logos/           # Team logos optimized for LED
└── README.md
```

## Setup

1. Clone the repository
2. Install required dependencies
3. Configure hardware connections
4. Run the display system

## Usage

The system automatically fetches live sports data and displays it on the LED matrix with team logos and scores.

## Related Projects

- [TickerAPI](../tickerapi) - FastAPI backend that provides sports data