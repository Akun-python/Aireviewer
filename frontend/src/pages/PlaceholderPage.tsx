type PlaceholderPageProps = {
  title: string;
  description: string;
};

export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <section className="placeholder-panel">
      <div className="eyebrow">Planned Surface</div>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="placeholder-note">当前这一部分仍建议通过 Streamlit 使用，React 版先聚焦“智能校稿”主流程。</div>
    </section>
  );
}
