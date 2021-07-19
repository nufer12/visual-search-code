import { Component, OnInit, OnDestroy, ViewChild, ViewContainerRef, Input, ComponentFactoryResolver, ComponentRef } from '@angular/core';
import { APIGenericDataItem } from '../util/data-types';
import { CollectionItemComponent } from '../collection-item/collection-item.component';
import { GenericListItem } from '../util/generic-list';
import { ImageItemComponent } from '../image-item/image-item.component';
import { SearchItemComponent } from '../search-item/search-item.component';
import { ResultsItemComponent } from '../results-item/results-item.component';
import { FavoritesItemComponent} from '../favorites-item/favorites-item.component';
import { UserItemComponent } from '../user-item/user-item.component';

export const ListTypeItems = {
  'collection': CollectionItemComponent,
  'image': ImageItemComponent,
  'search': SearchItemComponent,
  'result': ResultsItemComponent,
  'favorite': FavoritesItemComponent,
  'user': UserItemComponent
}

@Component({
  selector: 'app-generic-list-item',
  templateUrl: './generic-list-item.component.html',
  styleUrls: ['./generic-list-item.component.css'],
  // entryComponents: Object.values(ListTypeItems), // --> das geht kaputt wenn man bei Production uglify laufen lässt :/
  entryComponents: [
    CollectionItemComponent,
    ImageItemComponent,
    SearchItemComponent,
    ResultsItemComponent,
    FavoritesItemComponent,
    UserItemComponent
  ]
})
export class GenericListItemComponent implements OnInit, OnDestroy {

  @ViewChild('itemContainer', { read: ViewContainerRef })
  container: ViewContainerRef;
  @Input() type: string;
  private componentRef: ComponentRef<{}>;

  @Input() item : APIGenericDataItem;

  constructor(private componentFactoryResolver: ComponentFactoryResolver) { }

  ngOnInit() {
    if(this.type) {
      let factory = this.componentFactoryResolver.resolveComponentFactory(ListTypeItems[this.type]);
      this.componentRef = this.container.createComponent(factory);
      (<GenericListItem<any>>this.componentRef.instance).item = this.item;
    }
  }

  ngOnDestroy() {
    if (this.componentRef) {
        this.componentRef.destroy();
        this.componentRef = null;
    }
  }

}


