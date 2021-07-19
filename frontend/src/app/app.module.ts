import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule }   from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule, Routes } from '@angular/router';
import { FileUploadModule } from 'ng2-file-upload';

import { APIService } from './api.service';
import { NotificationService } from './notification.service';
import { FavoriteService } from './favorite.service';

import { AppComponent } from './app.component';
import { CollectionPageComponent } from './collection-page/collection-page.component';
import { CollectionListComponent } from './collection-list/collection-list.component';
import { GenericListComponent } from './generic-list/generic-list.component';
import { CollectionItemComponent } from './collection-item/collection-item.component';
import { GenericListItemComponent } from './generic-list-item/generic-list-item.component';
import { GenericListPaginationComponent } from './generic-list-pagination/generic-list-pagination.component';
import { GenericListFilterComponent } from './generic-list-filter/generic-list-filter.component';
import { ImageListComponent } from './image-list/image-list.component';
import { ImageItemComponent } from './image-item/image-item.component';
import { SearchListComponent } from './search-list/search-list.component';
import { SearchItemComponent } from './search-item/search-item.component';
import { ImageResultsComponent } from './image-results/image-results.component';
import { ResultsListComponent } from './results-list/results-list.component';
import { ResultsItemComponent } from './results-item/results-item.component';
import { FavoritesListComponent } from './favorites-list/favorites-list.component';
import { FavoritesItemComponent } from './favorites-item/favorites-item.component';
import { ImagePageComponent } from './image-page/image-page.component';
import { ImageSearchToolComponent } from './image-search-tool/image-search-tool.component';
import { CollectionInfoComponent } from './collection-info/collection-info.component';
import { IndicesListComponent } from './indices-list/indices-list.component';
import { ReviewComponent } from './review/review.component';
import { NewCollectionComponent } from './new-collection/new-collection.component';
import { NewIndexComponent } from './new-index/new-index.component';
import { UserItemComponent } from './user-item/user-item.component';
import { UserListComponent } from './user-list/user-list.component';
import { UserPageComponent } from './user-page/user-page.component';
import { LoginComponent } from './login/login.component';
import { NotificationComponent } from './notification/notification.component';
import { GenericListScalingComponent } from './generic-list-scaling/generic-list-scaling.component';
import { NewUserComponent } from './new-user/new-user.component';
import { ImageBoxesComponent } from './image-boxes/image-boxes.component';
import { ImageBoxDrawComponent } from './image-box-draw/image-box-draw.component';
import { IndexInfoModalComponent } from './index-info-modal/index-info-modal.component';
import { ImageSearchListComponent } from './image-search-list/image-search-list.component';
import { ImageRetrievalListComponent } from './image-retrieval-list/image-retrieval-list.component';
import { UploadDataComponent } from './upload-data/upload-data.component';
import { TsneComponent } from './tsne/tsne.component';
import { JobsComponent } from './jobs/jobs.component';


const appRoutes: Routes = [
  { path: 'collections',
    component: CollectionListComponent
  },
  { path: 'collection/:id',
    component: CollectionPageComponent,
    children: [
      { path: '', redirectTo: 'info', pathMatch: 'full'},
      { path: 'info', component: CollectionInfoComponent, data: {
        active: 1
      }},
      { path: 'images', component: ImageListComponent, data: {
        active: 2
      }},
      { path: 'image/:imageid', component: ImagePageComponent, data: {
        active: 2
      }},
      { path: 'image/:imageid/searches', component: ImageSearchListComponent, data: {
        active: 2
      }},
      { path: 'image/:imageid/results', component: ImageRetrievalListComponent, data: {
        active: 2
      }},
      { path: 'indices', component: IndicesListComponent, data: {
        active: 3
      }},
      { path: 'searches', component: SearchListComponent, data: {
        active: 4
      }},
      { path: 'search/:searchid', component: ResultsListComponent, data: {
        active: 4
      }},
      { path: 'search/:searchid/favorites', component: FavoritesListComponent, data: {
        active: 4
      }},
      { path: 'search/:searchid/tsne', component: TsneComponent, data: {
        active: 4
      }},
      { path: 'upload', component: UploadDataComponent, data: {
        active: 5
      }},
      { path: 'review', component: ReviewComponent, data: {
          active: 6
      }}
    ]
  },
  {
    path: 'resources',
    // component: ResourcesComponent
    component: JobsComponent
  },
  {
    path: 'users',
    component: UserListComponent
  },
  {
    path: 'user/:id',
    component: UserPageComponent
  },
  { path: '',
    redirectTo: '/collections',
    pathMatch: 'full'
  }
];






@NgModule({
  declarations: [
    AppComponent,
    CollectionPageComponent,
    CollectionListComponent,
    GenericListComponent,
    CollectionItemComponent,
    GenericListItemComponent,
    GenericListPaginationComponent,
    GenericListFilterComponent,
    ImageListComponent,
    ImageItemComponent,
    SearchListComponent,
    SearchItemComponent,
    ImageResultsComponent,
    ResultsListComponent,
    ResultsItemComponent,
    FavoritesListComponent,
    FavoritesItemComponent,
    ImagePageComponent,
    ImageSearchToolComponent,
    CollectionInfoComponent,
    IndicesListComponent,
    ReviewComponent,
    // UploadComponent,
    NewCollectionComponent,
    NewIndexComponent,
    UserItemComponent,
    UserListComponent,
    UserPageComponent,
    LoginComponent,
    NotificationComponent,
    GenericListScalingComponent,
    NewUserComponent,
    ImageBoxesComponent,
    ImageBoxDrawComponent,
    IndexInfoModalComponent,
    ImageSearchListComponent,
    ImageRetrievalListComponent,
    UploadDataComponent,
    TsneComponent,
    JobsComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    RouterModule.forRoot(
      appRoutes,
      { enableTracing: false,
        paramsInheritanceStrategy: 'always' } // <-- debugging purposes only
    ),
    FileUploadModule
  ],
  providers: [
    APIService,
    NotificationService,
    FavoriteService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
