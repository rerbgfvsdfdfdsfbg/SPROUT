const defaultState = {
  domain: ""
}

export const domainReducer = (state = defaultState, action) => {
  switch (action.type) {
    case "SET_DOMAIN":
      return {...state, domain: action.payload}
    
    default:
      return state
  }
}