import { configureStore } from "@reduxjs/toolkit";
import incidentsReducer from "./incidentSlice";

const store = configureStore({ reducer: { incidents: incidentsReducer } });
export default store;
