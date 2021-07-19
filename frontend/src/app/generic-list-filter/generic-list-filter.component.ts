import { Component, OnInit, Input, ViewChild, ViewContainerRef, ComponentRef, ComponentFactoryResolver } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { ManagedSubs } from '../util/managed-subs';
@Component({
  selector: 'app-generic-list-filter',
  templateUrl: './generic-list-filter.component.html',
  styleUrls: ['./generic-list-filter.component.scss']
})
export class GenericListFilterComponent extends ManagedSubs implements OnInit {

  private _queryParams;

  @Input() scheme : {type: string, name: string, placeholder: string}[] = [];
  public filter = {};

  // @ViewChild('itemContainer', { read: ViewContainerRef })
  // container: ViewContainerRef;
  // @Input() type: string;
  // private componentRef: ComponentRef<{}>;

  constructor(private router : Router, private route: ActivatedRoute, private componentFactoryResolver: ComponentFactoryResolver) {
    super();
  }

  ngOnInit() {
    // if(this.type) {
    //   let factory = this.componentFactoryResolver.resolveComponentFactory(ListTypeFilters[this.type]);
    //   this.componentRef = this.container.createComponent(factory);
    //   (<GenericListFilter>this.componentRef.instance).requireUpdate.subscribe(
    //     newFilter => {
    //       Object.keys(newFilter).map(el => {
    //         if(typeof newFilter[el] == 'boolean') {
    //           if(newFilter[el]) {
    //             newFilter[el] = 1;
    //           } else {
    //             newFilter[el] = 0;
    //           }
    //         }
    //       });


    //       this.update(newFilter);
    //     }
    //   )
    // }

    this.manageSub('getParams', this.route.queryParams.subscribe(queryParams => {
      this._queryParams = queryParams;
      this.filter = Object.assign({}, queryParams);
    }));
  }

  update() {
    this.router.navigate([], {queryParams: this.updateQueryParams(this.filter)});
  }

  updateQueryParams(newParams) {
    return Object.assign({}, this._queryParams, newParams);
  }


}
