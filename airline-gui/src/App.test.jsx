import React from "react";
import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders the application title", () => {
  render(React.createElement(App));
  const titleElement = screen.getByText(/Airline Reservation System GUI/i);
  expect(titleElement).toBeInTheDocument();
});
