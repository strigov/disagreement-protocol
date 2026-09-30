import type { ReactNode } from "react";
import type { ProtocolRow } from "@/lib/types";

export type EditableField = "point_label" | "party_1_text" | "party_2_text" | "agreed_text";
export interface ProtocolColumn { field: EditableField; header: string; label: string }
export type ClauseFilterValue = "all" | "attention" | "unreviewed";
/** Ячейки создаются в рендере контейнера, чтобы input/textarea не пересоздавались при наборе. */
export type RenderCell = (row: ProtocolRow, field: EditableField, label: string) => ReactNode;
