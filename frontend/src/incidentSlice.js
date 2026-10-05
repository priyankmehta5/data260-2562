import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api from "./api";

const message = (error) => error.response?.data?.detail || error.message || "Request failed";
export const fetchIncidents = createAsyncThunk("incidents/fetch", async (_, { rejectWithValue }) => {
  try { return (await api.get("/api/incidents?skip=0&limit=200")).data; }
  catch (error) { return rejectWithValue(message(error)); }
});
export const fetchIncident = createAsyncThunk("incidents/fetchOne", async (id, { rejectWithValue }) => {
  try { return (await api.get("/api/incidents/" + id)).data; }
  catch (error) { return rejectWithValue(message(error)); }
});
export const createIncident = createAsyncThunk("incidents/create", async (payload, { rejectWithValue }) => {
  try { return (await api.post("/api/incidents", payload)).data; }
  catch (error) { return rejectWithValue(message(error)); }
});
export const updateIncident = createAsyncThunk("incidents/update", async ({ id, changes }, { rejectWithValue }) => {
  try { return (await api.put("/api/incidents/" + id, changes)).data; }
  catch (error) { return rejectWithValue(message(error)); }
});
export const deleteIncident = createAsyncThunk("incidents/delete", async (id, { rejectWithValue }) => {
  try { await api.delete("/api/incidents/" + id); return id; }
  catch (error) { return rejectWithValue(message(error)); }
});

const slice = createSlice({
  name: "incidents",
  initialState: { items: [], status: "idle", error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(fetchIncidents.pending, (state) => { state.status = "loading"; state.error = null; });
    builder.addCase(fetchIncidents.fulfilled, (state, action) => { state.status = "succeeded"; state.items = action.payload; });
    builder.addCase(fetchIncidents.rejected, (state, action) => { state.status = "failed"; state.error = action.payload; });
    builder.addCase(createIncident.fulfilled, (state, action) => { state.items.push(action.payload); });
    builder.addCase(updateIncident.fulfilled, (state, action) => {
      const index = state.items.findIndex((item) => item.id === action.payload.id);
      if (index >= 0) state.items[index] = action.payload;
    });
    builder.addCase(deleteIncident.fulfilled, (state, action) => {
      state.items = state.items.filter((item) => item.id !== action.payload);
    });
  },
});
export default slice.reducer;
