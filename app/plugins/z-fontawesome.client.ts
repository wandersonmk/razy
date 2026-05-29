import { library, config } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { 
  faHome,
  faUsers,
  faBuilding,
  faChartBar,
  faFileAlt,
  faCog,
  faSignOutAlt,
  faUser,
  faBell,
  faLifeRing,
  faBars,
  faTimes,
  faExclamationTriangle,
  faTimesCircle,
  faInfoCircle,
  faCheckCircle,
  faRobot,
  faQuestionCircle,
  faShoppingCart,
  faUtensils,
  faTrash,
  faTrashAlt,
  faFilePdf,
  faFileExcel,
  faPhone,
  faComments,
  faFilter,
  faDatabase,
  faTicket,
  faBolt
} from '@fortawesome/free-solid-svg-icons'

// This is important, we are going to let Nuxt worry about the CSS
config.autoAddCss = false

// You can add your icons directly in this plugin. See other examples for how you
// can add other styles or just individual icons.
library.add(
  faHome,
  faUsers,
  faBuilding,
  faChartBar,
  faFileAlt,
  faCog,
  faSignOutAlt,
  faUser,
  faBell,
  faLifeRing,
  faBars,
  faTimes,
  faExclamationTriangle,
  faTimesCircle,
  faInfoCircle,
  faCheckCircle,
  faRobot,
  faQuestionCircle,
  faShoppingCart,
  faUtensils,
  faTrash,
  faTrashAlt,
  faFilePdf,
  faFileExcel,
  faPhone,
  faComments,
  faFilter,
  faDatabase,
  faTicket,
  faBolt
)

export default defineNuxtPlugin({
  name: 'fontawesome',
  parallel: false,
  setup(nuxtApp) {
    if (process.client) {
      console.log('[FontAwesome Plugin] Registrando componente...')
      nuxtApp.vueApp.component('font-awesome-icon', FontAwesomeIcon)
      nuxtApp.vueApp.component('FontAwesomeIcon', FontAwesomeIcon)
      console.log('[FontAwesome Plugin] Componente registrado com sucesso')
    }
  }
})
