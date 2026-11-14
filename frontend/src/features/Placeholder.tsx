/** 未交付功能的占位页，避免导航到空白。 */
export default function Placeholder({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="card text-center py-16">
      <h1 className="text-lg font-semibold mb-2">{title}</h1>
      <p className="note">{hint}</p>
    </div>
  );
}
