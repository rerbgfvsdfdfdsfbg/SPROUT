const defaultState = {
  domain: "",
  sitemap: []
}

export const domainReducer = (state = defaultState, action) => {
  switch (action.type) {
    case "SET_DOMAIN":
      return {...state, domain: action.payload}
    case "SET_SITEMAP":
      return {...state, sitemap: action.payload}
    
    default:
      return state
  }
}