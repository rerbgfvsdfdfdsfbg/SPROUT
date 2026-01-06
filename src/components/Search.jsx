import './styles/search.css'
import { useDispatch, useSelector } from "react-redux";

export default function Search() {

  const dispatch = useDispatch()
  const domain = useSelector(state => state.domain.domain)
  let sitemap;

  const updateInput = event => {
    dispatch({type:"SET_DOMAIN", payload:event.target.value})
  }
  const submitInput = event => {
    event.preventDefault() 
    console.log(domain)
    fetch('/api/scan?domain=' + domain)
      .then(res => res.json())
      .then(data => {
        sitemap = data['sitemap']
        console.log(sitemap)
        dispatch({type:"SET_SITEMAP", payload:sitemap})
      })
  }

  return (
    <div className="search-container">
      <form onSubmit={submitInput}>
        <input onChange={updateInput} id='input'></input>
      </form>
    </div>
  );
}