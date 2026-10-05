import { render } from "./render";
import { screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Icon } from "@/components/icons/Icon";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Notice } from "@/components/ui/Notice";
import { ErrorState } from "@/components/ui/States";
import { WorkspaceShell } from "@/components/WorkspaceShell";

test("dialog is named by its title, closes on cancel and returns focus", async () => {
  const onClose = vi.fn();
  function Harness() {
    const [open, setOpen] = useState(false);
    return <>
      <Button variant="primary" onClick={() => setOpen(true)}>Открыть</Button>
      {open && <Dialog title="Сохранить протокол" onClose={() => { onClose(); setOpen(false); }}>Содержимое</Dialog>}
    </>;
  }
  render(<Harness />);
  const opener = screen.getByRole("button", { name: "Открыть" });
  await userEvent.click(opener);
  const dialog = screen.getByRole("dialog", { name: "Сохранить протокол" });
  fireEvent(dialog, new Event("cancel", { cancelable: true }));
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
});

test("non-dismissible dialog ignores Escape and disables its close button", () => {
  const onClose = vi.fn();
  render(<Dialog title="Сохраняем" dismissible={false} onClose={onClose}>…</Dialog>);
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Закрыть" })).toBeDisabled();
});

test("error state is an alert with a working retry", async () => {
  const onRetry = vi.fn();
  render(<ErrorState title="Не удалось загрузить" text="Сервер недоступен" onRetry={onRetry} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Не удалось загрузить");
  expect(screen.getByRole("alert")).toHaveTextContent("Сервер недоступен");
  await userEvent.click(screen.getByRole("button", { name: "Повторить" }));
  expect(onRetry).toHaveBeenCalledTimes(1);
});

test("notice forwards its live role, icons are decorative unless labelled, buttons do not submit", () => {
  const { container } = render(<>
    <Notice role="status">Готово</Notice>
    <Icon name="check" label="Проверен вами" />
    <form><Button variant="ghost">Действие</Button></form>
  </>);
  expect(screen.getByRole("status")).toHaveTextContent("Готово");
  expect(screen.getByRole("img", { name: "Проверен вами" })).toBeInTheDocument();
  expect(container.querySelectorAll("svg[aria-hidden='true']").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Действие" })).toHaveAttribute("type", "button");
});

test("workspace shell marks the current step and links back to finished ones", async () => {
  const onNavigate = vi.fn();
  const { rerender } = render(<WorkspaceShell step={2} documentId="doc1">Контент</WorkspaceShell>);
  const steps = screen.getByRole("navigation", { name: "Этапы работы" });
  expect(steps.querySelector("[aria-current='step']")).toHaveTextContent("Стороны");
  expect(screen.getByRole("link", { name: /Документ/ })).toHaveAttribute("href", "/");
  expect(screen.queryByRole("link", { name: /Проверка протокола/ })).not.toBeInTheDocument();
  expect(screen.getByRole("group", { name: "Тема оформления" })).toBeInTheDocument();
  expect(document.querySelector("main#main-content")).toHaveTextContent("Контент");

  rerender(<WorkspaceShell step={2} documentId="doc1" onNavigate={onNavigate}>Контент</WorkspaceShell>);
  await userEvent.click(screen.getByRole("button", { name: /Документ/ }));
  expect(onNavigate).toHaveBeenCalledWith("/");
});
