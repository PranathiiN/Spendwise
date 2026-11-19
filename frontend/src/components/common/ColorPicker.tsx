import { PICKER_COLORS } from "../../utils/colors";

export function ColorPicker({ value, onChange }: { value: string; onChange: (color: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Color">
      {PICKER_COLORS.map((c) => (
        <button
          key={c}
          type="button"
          role="radio"
          aria-checked={value === c}
          aria-label={c}
          onClick={() => onChange(c)}
          className={`h-7 w-7 rounded-full ring-offset-2 transition ${value === c ? "ring-2 ring-slate-800" : "hover:scale-110"}`}
          style={{ backgroundColor: c }}
        />
      ))}
    </div>
  );
}
