import './styles/search.css'
import { useSelector } from "react-redux";

export default function Sitemap() {

  const sitemap = useSelector(state => state.domain.sitemap)
  console.log(">>> " + sitemap)

  return (
    <div className="container">
      <div>
        {sitemap.map(el => <div>{el}</div>)}
      </div>
    </div>
  );
}