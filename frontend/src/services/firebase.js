// src/services/firebase.js
// Firebase SDK initialisation for the Smart IT Helpdesk frontend.
// Analytics is initialised only in a browser environment (guard against SSR/test runners).

import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyA-U8wS90oPj82Yav5nwaNgcoEBGTRJ0U8",
  authDomain: "helpdesk-48108.firebaseapp.com",
  projectId: "helpdesk-48108",
  storageBucket: "helpdesk-48108.firebasestorage.app",
  messagingSenderId: "1021281605189",
  appId: "1:1021281605189:web:0a540175d8e14c89e6352c",
  measurementId: "G-VZ7KHF97CD",
};

// Initialise the Firebase app (singleton — safe to import from multiple modules)
const app = initializeApp(firebaseConfig);

// Initialise Analytics only when the environment supports it
// (browser with cookies/indexedDB available; not Node.js or unit-test runners)
let analytics = null;
isSupported().then((supported) => {
  if (supported) {
    analytics = getAnalytics(app);
  }
});

export { app, analytics };
