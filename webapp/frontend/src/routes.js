import Dashboard  from './pages/Dashboard.svelte'
import EdgeList   from './pages/EdgeList.svelte'
import EdgeDetail from './pages/EdgeDetail.svelte'
import Ranking    from './pages/Ranking.svelte'
import Oos        from './pages/Oos.svelte'
import CreateEdge from './pages/CreateEdge.svelte'

export const routes = {
  '/':            Dashboard,
  '/edges':       EdgeList,
  '/edges/:name': EdgeDetail,
  '/ranking':     Ranking,
  '/oos':         Oos,
  '/create':      CreateEdge,
}
