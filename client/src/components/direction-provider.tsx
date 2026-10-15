import { createContext, useContext } from "react"

const DirectionContext = createContext<"ltr" | "rtl">("rtl")
export function DirectionProvider({ dir, children }: { dir: "ltr" | "rtl"; children: React.ReactNode }) { return <DirectionContext.Provider value={dir}>{children}</DirectionContext.Provider> }
export const useDirection = () => useContext(DirectionContext)
