import type { ProtocolForm } from "@/lib/types";

export const FORM: ProtocolForm = {
  title: "Протокол разногласий", contract_reference: "поставки № 12", place: "", date: "",
  opening_text: "Стороны договорились заключить договор с учетом протокола разногласий.",
  closing_text: "Во всем остальном стороны руководствуются условиями договора.",
  point_title: "Пункт договора", original_title: "Редакция Поставщика",
  proposed_title: "Редакция Покупателя", agreed_title: "Согласованная редакция",
  mark_drafting_signature: true,
  signatures: {
    supplier: { name: "ООО Поставщик", role: "Поставщик", position: "", full_name: "" },
    buyer: { name: "ООО Покупатель", role: "Покупатель", position: "", full_name: "" },
  },
};
