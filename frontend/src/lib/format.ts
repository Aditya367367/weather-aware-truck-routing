const timeFmt = new Intl.DateTimeFormat(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });

export const formatTime = (iso: string | Date) => timeFmt.format(new Date(iso));

export function formatDuration(seconds: number): string {
  const total = Math.round(seconds / 60);
  const h = Math.floor(total / 60);
  return h ? `${h} h ${total % 60} min` : `${total} min`;
}

export const formatMiles = (mi: number) => `${Math.round(mi).toLocaleString()} mi`;

/** Value for <input type="datetime-local"> in the viewer's local time. */
export function toLocalInput(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export const nextHour = (): Date => {
  const d = new Date();
  d.setHours(d.getHours() + 1, 0, 0, 0);
  return d;
};

export const routeName = (id: string) => `Route ${String.fromCharCode(64 + Number(id.slice(1)))}`;
