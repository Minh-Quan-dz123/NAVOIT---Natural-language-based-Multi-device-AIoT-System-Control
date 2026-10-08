#include "HTTPServer.h"
#include "WiFiManager.h"

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

namespace
{
    WebServer server(80); // port 80

    // code HTML giao diện web
    const char INDEX_HTML[] PROGMEM = R"rawliteral(
    <!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 WiFi Manager</title>
    <style>
        * {box-sizing: border-box;}

        :root {
            --bg: #f5f7fb;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --border: #e5e7eb;

            --text: #111827;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;

            --primary: #2563eb;
            --primary-hover: #1d4ed8;

            --success: #16a34a;
            --success-bg: #dcfce7;

            --danger: #dc2626;
            --danger-hover: #b91c1c;
            --danger-bg: #fee2e2;

            --warning: #d97706;
            --warning-bg: #fef3c7;

            --radius: 14px;
        }

        body {
            margin: 0;
            min-height: 100vh;

            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                Helvetica,
                sans-serif;

            background:
                radial-gradient(
                    circle at top right,
                    #eaf2ff 0,
                    transparent 30%
                ),
                var(--bg);

            color: var(--text);
        }

        /* =========================================
           LAYOUT
           ========================================= */

        .container {
            width: 100%;
            max-width: 920px;

            margin: 0 auto;
            padding: 36px 24px 50px;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        /* =========================================
           HEADER
           ========================================= */

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;

            gap: 20px;
            margin-bottom: 28px;
        }

        .header-left {
            min-width: 0;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;

            margin-bottom: 7px;
        }

        .brand-icon {
            width: 42px;
            height: 42px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 12px;

            background: #eff6ff;
            color: var(--primary);

            font-size: 21px;
        }

        .header h1 {
            margin: 0;

            font-size: 25px;
            font-weight: 700;

            letter-spacing: -0.5px;
        }

        .header p {
            margin: 0;

            color: var(--text-secondary);

            font-size: 14px;
        }

        .device-status {
            display: flex;
            align-items: center;
            gap: 8px;

            padding: 9px 13px;

            background: var(--surface);

            border: 1px solid var(--border);
            border-radius: 999px;

            color: var(--text-secondary);

            font-size: 13px;
            font-weight: 600;

            white-space: nowrap;
        }

        .status-dot {
            width: 8px;
            height: 8px;

            border-radius: 50%;

            background: var(--text-muted);
        }

        /* =========================================
           CARD
           ========================================= */

        .card {
            background: rgba(255, 255, 255, 0.95);

            border: 1px solid var(--border);
            border-radius: var(--radius);

            padding: 20px;

            box-shadow:
                0 2px 8px rgba(15, 23, 42, 0.03);

            transition:
                box-shadow 0.2s ease;
        }

        .card:hover {
            box-shadow:
                0 8px 24px rgba(15, 23, 42, 0.06);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;

            gap: 12px;

            margin-bottom: 18px;
        }

        .card-title-wrapper {
            display: flex;
            align-items: center;
            gap: 11px;
        }

        .card-icon {
            width: 34px;
            height: 34px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 9px;

            background: #eff6ff;
            color: var(--primary);

            font-size: 16px;
        }

        .card-title {
            margin: 0;

            font-size: 16px;
            font-weight: 650;
        }

        .card-subtitle {
            margin: 3px 0 0;

            color: var(--text-secondary);

            font-size: 12px;
        }

        /* =========================================
           CONNECTION
           ========================================= */

        .connection-main {
            display: flex;
            align-items: center;

            gap: 14px;

            padding: 16px;

            margin-bottom: 14px;

            background: var(--surface-soft);

            border: 1px solid var(--border);
            border-radius: 12px;
        }

        .connection-icon {
            width: 46px;
            height: 46px;

            flex-shrink: 0;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 12px;

            background: #f3f4f6;
            color: var(--text-muted);

            font-size: 22px;
        }

        .connection-info {
            min-width: 0;
        }

        .connection-label {
            margin-bottom: 3px;

            color: var(--text-secondary);

            font-size: 11px;
            font-weight: 600;

            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .connection-ssid {
            overflow: hidden;

            color: var(--text);

            font-size: 17px;
            font-weight: 700;

            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .connection-status {
            margin-top: 3px;

            color: var(--text-muted);

            font-size: 12px;
            font-weight: 600;
        }

        .status-grid {
            display: grid;

            grid-template-columns: 1fr 1fr;

            gap: 10px;
        }

        .status-item {
            padding: 12px;

            background: var(--surface-soft);

            border: 1px solid var(--border);
            border-radius: 10px;
        }

        .status-label {
            display: block;

            margin-bottom: 5px;

            color: var(--text-muted);

            font-size: 11px;
            font-weight: 600;

            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .status-value {
            display: block;

            color: var(--text);

            font-size: 13px;
            font-weight: 650;

            word-break: break-word;
        }

        .status-connected {
            color: var(--success);
        }

        .status-connecting {
            color: var(--warning);
        }

        .status-failed {
            color: var(--danger);
        }

        /* =========================================
           FORM
           ========================================= */

        .form-group {
            margin-bottom: 15px;
        }

        .form-label {
            display: block;

            margin-bottom: 7px;

            color: #374151;

            font-size: 12px;
            font-weight: 650;
        }

        input {
            width: 100%;

            padding: 11px 12px;

            background: #fff;

            border: 1px solid #d1d5db;
            border-radius: 9px;

            outline: none;

            color: var(--text);

            font-family: inherit;
            font-size: 13px;
        }

        input::placeholder {
            color: #9ca3af;
        }

        input:focus {
            border-color: var(--primary);

            box-shadow:
                0 0 0 3px rgba(37, 99, 235, 0.10);
        }

        .password-wrapper {
            position: relative;
        }

        .password-wrapper input {
            padding-right: 45px;
        }

        .password-toggle {
            position: absolute;

            right: 6px;
            top: 50%;

            transform: translateY(-50%);

            width: 32px;
            height: 32px;

            padding: 0;

            border: none;
            background: transparent;

            color: var(--text-secondary);

            cursor: pointer;
        }

        /* =========================================
           BUTTONS
           ========================================= */

        .button-row {
            display: flex;

            gap: 8px;
            flex-wrap: wrap;

            margin-top: 18px;
        }

        button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 7px;

            padding: 10px 14px;

            border: 1px solid transparent;
            border-radius: 9px;

            font-family: inherit;
            font-size: 13px;
            font-weight: 650;

            cursor: pointer;

            transition:
                background 0.2s ease,
                border-color 0.2s ease,
                transform 0.1s ease;
        }

        button:active {
            transform: translateY(1px);
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-hover);
        }

        .btn-secondary {
            background: #f3f4f6;
            color: #374151;

            border-color: #e5e7eb;
        }

        .btn-secondary:hover {
            background: #e5e7eb;
        }

        .btn-danger {
            background: white;
            color: var(--danger);

            border-color: #fecaca;
        }

        .btn-danger:hover {
            background: var(--danger-bg);
        }

        .btn-small {
            padding: 7px 10px;

            font-size: 11px;
        }

        /* =========================================
           SECTION HEADER
           ========================================= */

        .section-header {
            display: flex;

            align-items: center;
            justify-content: space-between;

            gap: 12px;

            margin-bottom: 16px;
        }

        /* =========================================
           WIFI LIST
           ========================================= */

        .wifi-list {
            display: flex;

            flex-direction: column;

            gap: 8px;
        }

        .wifi-item {
            display: flex;

            align-items: center;
            justify-content: space-between;

            gap: 15px;

            padding: 13px;

            background: var(--surface);

            border: 1px solid var(--border);
            border-radius: 10px;

            cursor: pointer;

            transition:
                background 0.2s ease,
                border-color 0.2s ease;
        }

        .wifi-item:hover {
            background: #f8fafc;
            border-color: #d1d5db;
        }

        .wifi-info {
            display: flex;
            align-items: center;

            gap: 12px;

            min-width: 0;
        }

        .wifi-icon {
            width: 34px;
            height: 34px;

            flex-shrink: 0;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 8px;

            background: #eff6ff;
            color: var(--primary);

            font-size: 15px;
        }

        .wifi-details {
            min-width: 0;
        }

        .wifi-ssid {
            margin-bottom: 3px;

            color: var(--text);

            font-size: 13px;
            font-weight: 650;

            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .wifi-bssid {
            color: var(--text-muted);

            font-size: 10px;
            font-family: monospace;
        }

        .wifi-right {
            display: flex;
            align-items: center;

            gap: 12px;

            flex-shrink: 0;
        }

        .wifi-rssi {
            color: var(--text-secondary);

            font-size: 11px;
            font-weight: 650;

            white-space: nowrap;
        }

        .wifi-signal {
            display: flex;
            align-items: flex-end;

            gap: 2px;

            height: 13px;
        }

        .wifi-signal span {
            width: 3px;

            border-radius: 2px;

            background: #d1d5db;
        }

        .wifi-signal span:nth-child(1) {
            height: 4px;
        }

        .wifi-signal span:nth-child(2) {
            height: 7px;
        }

        .wifi-signal span:nth-child(3) {
            height: 10px;
        }

        .wifi-signal span:nth-child(4) {
            height: 13px;
        }

        /* =========================================
           EMPTY
           ========================================= */

        .empty {
            padding: 30px 20px;

            text-align: center;

            color: var(--text-muted);

            font-size: 13px;

            border: 1px dashed #d1d5db;
            border-radius: 10px;

            background: #fafafa;
        }

        .empty-icon {
            margin-bottom: 8px;

            font-size: 24px;
        }

        .empty-title {
            margin-bottom: 4px;

            color: #6b7280;

            font-weight: 600;
        }

        .empty-text {
            font-size: 12px;
        }

        /* =========================================
           FOOTER
           ========================================= */

        .footer {
            margin-top: 22px;

            text-align: center;

            color: var(--text-muted);

            font-size: 11px;
        }

        /* =========================================
           RESPONSIVE
           ========================================= */

        @media (max-width: 720px) {

            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .full-width {
                grid-column: auto;
            }

        }

        @media (max-width: 560px) {

            .container {
                padding: 22px 14px 35px;
            }

            .header {
                align-items: flex-start;
                flex-direction: column;
            }

            .device-status {
                align-self: flex-start;
            }

            .card {
                padding: 16px;
            }

            .status-grid {
                grid-template-columns: 1fr;
            }

            .button-row {
                flex-direction: column;
            }

            .button-row button {
                width: 100%;
            }

            .wifi-item {
                align-items: flex-start;
            }

            .wifi-right {
                flex-direction: column;
                align-items: flex-end;

                gap: 5px;
            }

        }

    </style>

</head>

<body>

<div class="container">

    <!-- =========================================
         HEADER
         ========================================= -->

    <header class="header">

        <div class="header-left">

            <div class="brand">

                <div class="brand-icon">
                    📡
                </div>

                <h1>
                    ESP32 WiFi Manager
                </h1>

            </div>

            <p>
                Configure and manage your ESP32 network connection
            </p>

        </div>

        <div class="device-status">

            <span
                class="status-dot"
                id="deviceStatusDot">
            </span>

            <span id="deviceStatus">
                ESP32
            </span>

        </div>

    </header>


    <div class="dashboard-grid">


        <!-- =========================================
             CURRENT CONNECTION
             ========================================= -->

        <div class="card">

            <div class="card-header">

                <div class="card-title-wrapper">

                    <div class="card-icon">
                        📶
                    </div>

                    <div>

                        <h2 class="card-title">
                            Current Connection
                        </h2>

                        <p class="card-subtitle">
                            Active WiFi connection
                        </p>

                    </div>

                </div>

            </div>


            <div class="connection-main">

                <div class="connection-icon"
                     id="connectionIcon">

                    📡

                </div>

                <div class="connection-info">

                    <div class="connection-label">
                        Connected to
                    </div>

                    <div class="connection-ssid"
                         id="currentSSID">

                        —

                    </div>

                    <div class="connection-status"
                         id="status">

                        ● Disconnected

                    </div>

                </div>

            </div>


            <div class="status-grid">

                <div class="status-item">

                    <span class="status-label">
                        Signal
                    </span>

                    <span class="status-value"
                          id="rssi">

                        —

                    </span>

                </div>


                <div class="status-item">

                    <span class="status-label">
                        IP Address
                    </span>

                    <span class="status-value"
                          id="ip">

                        —

                    </span>

                </div>


                <div class="status-item"
                     style="grid-column: 1 / -1;">

                    <span class="status-label">
                        MAC Address
                    </span>

                    <span class="status-value"
                          id="mac">

                        —

                    </span>

                </div>

            </div>

        </div>


        <!-- =========================================
             CONNECT WIFI
             ========================================= -->

        <div class="card">

            <div class="card-header">

                <div class="card-title-wrapper">

                    <div class="card-icon">
                        🔗
                    </div>

                    <div>

                        <h2 class="card-title">
                            Connect to WiFi
                        </h2>

                        <p class="card-subtitle">
                            Connect ESP32 to a network
                        </p>

                    </div>

                </div>

            </div>


            <div class="form-group">

                <label class="form-label"
                       for="ssid">

                    WiFi Name (SSID)

                </label>

                <input
                    id="ssid"
                    type="text"
                    placeholder="Enter WiFi name">

            </div>


            <div class="form-group">

                <label class="form-label"
                       for="password">

                    Password

                </label>

                <div class="password-wrapper">

                    <input
                        id="password"
                        type="password"
                        placeholder="Enter WiFi password">

                    <button
                        class="password-toggle"
                        type="button"
                        onclick="togglePassword()"
                        aria-label="Show password">

                        👁

                    </button>

                </div>

            </div>


            <div class="button-row">

                <button
                    class="btn-primary"
                    onclick="connectWiFi()">

                    Connect

                </button>

                <button
                    class="btn-secondary"
                    onclick="cancelConnect()">

                    Cancel

                </button>

                <button
                    class="btn-danger"
                    onclick="disconnectWiFi()">

                    Disconnect

                </button>

            </div>

        </div>


        <!-- =========================================
             AVAILABLE WIFI
             ========================================= -->

        <div class="card full-width">

            <div class="section-header">

                <div class="card-title-wrapper">

                    <div class="card-icon">
                        📡
                    </div>

                    <div>

                        <h2 class="card-title">
                            Available WiFi
                        </h2>

                        <p class="card-subtitle">
                            Networks detected nearby
                        </p>

                    </div>

                </div>

                <button
                    class="btn-primary"
                    id="scanButton"
                    onclick="scanWiFi()">

                    ↻ Scan

                </button>

            </div>


            <div id="scanResults">

                <div class="empty">

                    <div class="empty-icon">
                        📡
                    </div>

                    <div class="empty-title">
                        No WiFi networks
                    </div>

                    <div class="empty-text">
                        Click Scan to search for available networks.
                    </div>

                </div>

            </div>

        </div>


        <!-- =========================================
             SAVED WIFI
             ========================================= -->

        <div class="card full-width">

            <div class="section-header">

                <div class="card-title-wrapper">

                    <div class="card-icon">
                        💾
                    </div>

                    <div>

                        <h2 class="card-title">
                            Saved WiFi
                        </h2>

                        <p class="card-subtitle">
                            Networks stored on ESP32
                        </p>

                    </div>

                </div>

            </div>


            <div class="empty">

                <div class="empty-icon">
                    💾
                </div>

                <div class="empty-title">
                    No saved networks
                </div>

                <div class="empty-text">
                    Saved WiFi networks will appear here.
                </div>

            </div>

        </div>


    </div>


    <div class="footer">

        ESP32 WiFi Manager · Local Network Configuration

    </div>

</div>


<script>

// ========================================================
// PASSWORD
// ========================================================

function togglePassword()
{
    const password =
        document.getElementById("password");

    password.type =
        password.type === "password"
            ? "text"
            : "password";
}


// ========================================================
// CONNECT
// ========================================================

async function connectWiFi()
{
    const ssid =
        document.getElementById("ssid").value;

    const password =
        document.getElementById("password").value;

    if (!ssid)
    {
        return;
    }

    try
    {
        await fetch(
            "/connect",
            {
                method: "POST",

                headers:
                {
                    "Content-Type":
                        "application/json"
                },

                body:
                    JSON.stringify(
                    {
                        ssid: ssid,
                        password: password
                    })
            });
    }
    catch (error)
    {
        console.error(
            "Connect error:",
            error);
    }
}


// ========================================================
// CANCEL CONNECT
// ========================================================

async function cancelConnect()
{
    try
    {
        await fetch(
            "/cancel",
            {
                method: "POST"
            });
    }
    catch (error)
    {
        console.error(
            "Cancel error:",
            error);
    }
}


// ========================================================
// DISCONNECT
// ========================================================

async function disconnectWiFi()
{
    try
    {
        await fetch(
            "/disconnect",
            {
                method: "POST"
            });
    }
    catch (error)
    {
        console.error(
            "Disconnect error:",
            error);
    }
}


// ========================================================
// SCAN
// ========================================================

async function scanWiFi()
{
    const container =
        document.getElementById(
            "scanResults");

    const scanButton =
        document.getElementById(
            "scanButton");

    scanButton.disabled = true;

    scanButton.innerText =
        "Scanning...";

    container.innerHTML = `
        <div class="empty">
            <div class="empty-icon">📡</div>
            <div class="empty-title">
                Scanning for WiFi networks
            </div>
            <div class="empty-text">
                Please wait...
            </div>
        </div>
    `;

    try
    {
        await fetch(
            "/scan",
            {
                method: "POST"
            });

        setTimeout(
            loadScanResults,
            5000);
    }
    catch (error)
    {
        console.error(
            "Scan error:",
            error);

        container.innerHTML = `
            <div class="empty">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">
                    Scan failed
                </div>
                <div class="empty-text">
                    Unable to start WiFi scan.
                </div>
            </div>
        `;

        scanButton.disabled = false;

        scanButton.innerText =
            "↻ Scan";
    }
}


// ========================================================
// LOAD SCAN RESULTS
// ========================================================

async function loadScanResults()
{
    const container =
        document.getElementById(
            "scanResults");

    const scanButton =
        document.getElementById(
            "scanButton");

    try
    {
        const response =
            await fetch(
                "/scan-results");

        const data =
            await response.json();

        container.innerHTML = "";

        if (!data.networks ||
            data.networks.length === 0)
        {
            container.innerHTML = `
                <div class="empty">
                    <div class="empty-icon">📡</div>
                    <div class="empty-title">
                        No WiFi networks found
                    </div>
                    <div class="empty-text">
                        No available networks were detected.
                    </div>
                </div>
            `;

            return;
        }

        data.networks.forEach(
            function(network)
            {
                const item =
                    document.createElement(
                        "div");

                item.className =
                    "wifi-item";

                item.onclick =
                    function()
                    {
                        document.getElementById(
                            "ssid").value =
                            network.ssid;
                    };

                const info =
                    document.createElement(
                        "div");

                info.className =
                    "wifi-info";

                const icon =
                    document.createElement(
                        "div");

                icon.className =
                    "wifi-icon";

                icon.innerText =
                    "📶";

                const details =
                    document.createElement(
                        "div");

                details.className =
                    "wifi-details";

                const ssid =
                    document.createElement(
                        "div");

                ssid.className =
                    "wifi-ssid";

                ssid.innerText =
                    network.ssid ||
                    "(Hidden Network)";

                const bssid =
                    document.createElement(
                        "div");

                bssid.className =
                    "wifi-bssid";

                bssid.innerText =
                    network.bssid || "—";

                details.appendChild(
                    ssid);

                details.appendChild(
                    bssid);

                info.appendChild(
                    icon);

                info.appendChild(
                    details);


                const right =
                    document.createElement(
                        "div");

                right.className =
                    "wifi-right";

                const signal =
                    document.createElement(
                        "div");

                signal.className =
                    "wifi-signal";

                for (
                    let i = 0;
                    i < 4;
                    i++
                )
                {
                    const bar =
                        document.createElement(
                            "span");

                    signal.appendChild(
                        bar);
                }

                const rssi =
                    document.createElement(
                        "div");

                rssi.className =
                    "wifi-rssi";

                rssi.innerText =
                    network.rssi +
                    " dBm";

                right.appendChild(
                    signal);

                right.appendChild(
                    rssi);


                item.appendChild(
                    info);

                item.appendChild(
                    right);

                container.appendChild(
                    item);
            });
    }
    catch (error)
    {
        console.error(
            "Load scan results error:",
            error);

        container.innerHTML = `
            <div class="empty">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">
                    Failed to load results
                </div>
                <div class="empty-text">
                    Unable to get WiFi scan results.
                </div>
            </div>
        `;
    }
    finally
    {
        scanButton.disabled = false;

        scanButton.innerText =
            "↻ Scan";
    }
}


// ========================================================
// STATUS
// ========================================================

async function updateStatus()
{
    try
    {
        const response =
            await fetch(
                "/status");

        const data =
            await response.json();


        // ------------------------------------------------
        // SSID
        // ------------------------------------------------

        document.getElementById(
            "currentSSID").innerText =
            data.ssid || "—";


        // ------------------------------------------------
        // RSSI
        // ------------------------------------------------

        if (
            data.status ===
            "CONNECTED"
        )
        {
            document.getElementById(
                "rssi").innerText =
                data.rssi + " dBm";
        }
        else
        {
            document.getElementById(
                "rssi").innerText =
                "—";
        }


        // ------------------------------------------------
        // IP
        // ------------------------------------------------

        document.getElementById(
            "ip").innerText =
            data.ip || "—";


        // ------------------------------------------------
        // MAC
        // ------------------------------------------------

        document.getElementById(
            "mac").innerText =
            data.mac || "—";


        // ------------------------------------------------
        // Status
        // ------------------------------------------------

        const statusElement =
            document.getElementById(
                "status");

        statusElement.className =
            "connection-status";


        if (
            data.status ===
            "CONNECTED"
        )
        {
            statusElement.classList.add(
                "status-connected");

            statusElement.innerText =
                "● Connected";
        }
        else if (
            data.status ===
            "CONNECTING"
        )
        {
            statusElement.classList.add(
                "status-connecting");

            statusElement.innerText =
                "● Connecting...";
        }
        else if (
            data.status ===
            "FAILED"
        )
        {
            statusElement.classList.add(
                "status-failed");

            statusElement.innerText =
                "● Connection failed";
        }
        else
        {
            statusElement.innerText =
                "● Disconnected";
        }


        // ------------------------------------------------
        // ESP32 status
        // ------------------------------------------------

        const deviceStatus =
            document.getElementById(
                "deviceStatus");

        const deviceStatusDot =
            document.getElementById(
                "deviceStatusDot");


        deviceStatus.innerText =
            "ESP32 Online";

        deviceStatusDot.style.background =
            "var(--success)";

    }
    catch (error)
    {
        console.error(
            "Status error:",
            error);

        document.getElementById(
            "deviceStatus").innerText =
            "ESP32 Offline";

        document.getElementById(
            "deviceStatusDot").style.background =
            "var(--danger)";
    }
}


// ========================================================
// AUTO UPDATE STATUS
// ========================================================

setInterval(
    updateStatus,
    1000);

updateStatus();

</script>

</body>

</html>

)rawliteral";
    
    // 1. GET/
    void handleRoot()
    {
        server.send(200, "text/html", INDEX_HTML);
        // 200 → HTTP status OK
        // "text/html" → dữ liệu trả về là HTML
        // INDEX_HTML → nội dung giao diện web
    }

    // 2. POST - connect
    void handleConnect()
    {
        if(!server.hasArg("plain")) //kiểm tra xem request có body dạng raw text hay không.
        {
            server.send(400, "application/json", "{\"error\":\"Missing JSON\"}");
            return;
        }
        
        // lấy toàn bộ nội dung body của http request và lưu vào biến body
        String body = server.arg("plain"); 
        // ví dụ FE gửi
        // POST /connect
        // Content-Type: application/json

        // {
        //     "ssid": "MyWiFi",
        //     "password": "12345678"
        // }
        // => body = "{\"ssid\":\"MyWiFi\",\"password\":\"12345678\"}";

        int ssidStart = body.indexOf("\"ssid\"");
        int passwordStart = body.indexOf("\"password\"");
        if(ssidStart < 0 || passwordStart < 0)
        {
            server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
            return;
        }

        // tách giá trị ssid và password ra khởi json bằng cách tìm vị trí các dấu "
        int ssidColon = body.indexOf(":", ssidStart);       // ví dụ "ssid":"MyWiFi"
        int ssidQuote1 = body.indexOf("\"", ssidColon + 1); // ví dụ "ssid":"MyWiFi"
        int ssidQuote2 = body.indexOf("\"", ssidQuote1 + 1);// ví dụ "ssid":"MyWiFi"

        int passColon = body.indexOf(":", passwordStart);
        int passQuote1 = body.indexOf("\"", passColon + 1);
        int passQuote2 = body.indexOf("\"", passQuote1 + 1);

        String ssid = body.substring(ssidQuote1 + 1, ssidQuote2);
        String password = body.substring(passQuote1 + 1, passQuote2);

        // DEBUG
        Serial.println("========== CONNECT REQUEST ==========");
        Serial.println("[HTTPServer] SSID: " + ssid);
        Serial.println("[HTTPServer] Password: " + password);
        Serial.println("=====================================");

        // gửi command cho WiFiManagerTask (chỉ là request thôi)
        bool result = WiFiManager::requestConnect(ssid, password);
        if(result)// gửi thành công yêu cầu
        {
            server.send(200, "application/json", "{\"success\":true}");
        }
        else
        {
            server.send(503, "application/json", "{\"success\":false}");
        }

    }
    // 3. post/cancel
    void handleCancel()
    {
        WiFiManager::requestCancelConnect();
        server.send(200, "application/json", "{\"success\":true}");
    }

    // 4. post/disconnect
    void handleDisconnect()
    {
        WiFiManager::requestDisconnect();
        server.send(200, "application/json", "{\"success\":true}");
    }

    // 5. post/scan
    void handleScan()
    {
        WiFiManager::requestScan();
        server.send(200, "application/json", "{\"success\":true}");
    }

    // 6. get /scan-results
    void handleScanResults()
    {
        String json ="{\"networks\":[";
        int count = WiFiManager::getScanCount();
        for(int i=0; i<count; i++)
        {
            ScannedWiFi wifi = WiFiManager::getScanResult(i);
            if(i>0)
            {
                json += ",";
            }
            json += "{";
            json += "\"ssid\":\"" + wifi.ssid + "\",";
            json += "\"rssi\":" + String(wifi.rssi) + ",";
            json += "\"bssid\":\"" + wifi.bssid + "\"";

            json += "}";
        }
        json += "]}";
        server.send(200, "application/json", json);
    } 

    // 7. get /status
    void handleStatus()
    {
        String status;

        switch (WiFiManager::getState())
        {
            case WiFiConnectionState::DISCONNECTED:
                status = "DISCONNECTED";
                break;

            case WiFiConnectionState::CONNECTING:
                status = "CONNECTING";
                break;

            case WiFiConnectionState::CONNECTED:
                status = "CONNECTED";
                break;

            case WiFiConnectionState::FAILED:
                status = "FAILED";
                break;
        }

        String json ="{";
        
        json += "\"ssid\":\"" + WiFiManager::getSSID() + "\",";
        json += "\"rssi\":" + String(WiFiManager::getRSSI()) + ",";
        json += "\"ip\":\"" + WiFiManager::getIP() + "\",";
        json += "\"mac\":\"" + WiFiManager::getMAC() + "\",";
        json += "\"status\":\"" +  status + "\"";
        json += "}";

        server.send(200,"application/json",json);
    }
}

void HTTPServer::begin()
{
    // đăng ký các thông tin
    // 1. đăng ký trang chính
    server.on("/", HTTP_GET, handleRoot);

    // 2. đăng ký hàm connect
    server.on("/connect", HTTP_POST, handleConnect);

    // 3. đăng ký hàm cancel
    server.on("/cancel", HTTP_POST, handleCancel);

    // 4. đăng ký hàm Disconnect
    server.on("/disconnect", HTTP_POST, handleDisconnect);

    // 5. đăng ký hàm scan
    server.on("/scan", HTTP_POST, handleScan);

    // 6. đăng ký hàm get scan result
    server.on("/scan-results", HTTP_GET, handleScanResults);

    // 7. đăng ký hàm get status
    server.on("/status", HTTP_GET, handleStatus);

    server.begin();

    // 8. HTTP server chạy bằng Task riêng
    xTaskCreatePinnedToCore([](void *parameter){
        while(true)
        {
            server.handleClient();// xử lý http request
            vTaskDelay(pdMS_TO_TICKS(5)); // nhường cpu cho task khác
        }
    }, 
    "HTTPServerTask",
    8192,
    nullptr,
    2,  // priority ( của wifi là 3)
    nullptr,
    1 // core số 1
    );

    Serial.println("[HTTPServer] Started");
    Serial.println("[HTTPServer] http://192.168.4.1");


}