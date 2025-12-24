"use client";

import { createContext, useContext, ReactNode } from "react";
import { HotelResponse } from "./api";

interface HotelContextType {
  hotel: HotelResponse;
  hotelId: number;
}

const HotelContext = createContext<HotelContextType | null>(null);

interface HotelProviderProps {
  hotel: HotelResponse;
  children: ReactNode;
}

export function HotelProvider({ hotel, children }: HotelProviderProps) {
  return (
    <HotelContext.Provider value={{ hotel, hotelId: hotel.id }}>
      {children}
    </HotelContext.Provider>
  );
}

export function useHotel(): HotelContextType {
  const context = useContext(HotelContext);
  if (!context) {
    throw new Error("useHotel must be used within a HotelProvider");
  }
  return context;
}

export function useHotelId(): number {
  const { hotelId } = useHotel();
  return hotelId;
}

